import argparse
import json
import re
import subprocess
import time

import redis

class start_vm:
    virsh = ['virsh', '-c', 'qemu:///system']

    def __init__(self, hostname, vm_name, vm_ip):
        self.hostname = hostname
        self.vm_name = vm_name
        self.vm_ip = vm_ip

    def __enter__(self):
        if self.hostname:
            return self.hostname

        out = subprocess.check_output(self.virsh + ['list --all'])
        status = re.search('%s\s+([^\n]*)' % self.vm_name, out).group(1)
        if status == 'shut off':
            subprocess.call(self.virsh + ['start %s' % self.vm_name])
            # wait max 30 seconds for the vm to be online
            for i in xrange(30):
                try:
                    subprocess.check_call(['ping', '-c1', self.vm_ip])
                    break
                except subprocess.CalledProcessError:
                    time.sleep(1)
        return self.vm_ip

    def __exit__(self, type, value, traceback):
        if not self.hostname:
            subprocess.call(self.virsh + ['shutdown %s' % self.vm_name])
            time.sleep(60)


def run(setup, server, vm_hostname, vm_name, vm_ip):
    s = redis.Redis(server)

    pull_request = json.loads(s.blpop('build_queue')[1])

    try:
        with start_vm(vm_hostname, vm_name, vm_ip) as vm_hostname:
            print '%s setup' % setup
            import fabfile
            fabfile.env.host_string = vm_hostname
            getattr(fabfile, '%s_setup' % setup)(
                    clone_url=pull_request['clone_url'],
                    sha=pull_request['sha'], force_clone=True)

            print '%s test' % setup
            test_results = getattr(fabfile, '%s_test' % setup)()
            test_results = test_results.splitlines()
            test_results = 'Automated test results for %s: %s\n\n%s\n' % (
                    pull_request['sha'], test_results[-1], test_results[-3])

            print test_results
            s.rpush('comment_queue', json.dumps({
                'pull_request_id': pull_request['pull_request_id'],
                'repo': pull_request['repo'],
                'test_results': test_results}))
    except:
        s.lpush('build_queue', json.dumps(pull_request))
        raise

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('setup', help='the name of the fabric task, e.g. "archive"')
    parser.add_argument('server', help='the hostname of the redis server')
    parser.add_argument('-H', dest='vm_hostname', help='the hostname of the vm to run the tasks')
    parser.add_argument('-n', dest='vm_name', help='the name of the vm in virt-manager')
    parser.add_argument('-i', dest='vm_ip', help='the ip address of the vm')
    args = parser.parse_args()

    run(args.setup, args.server, args.vm_hostname, args.vm_name, args.vm_ip)

if __name__ == '__main__':
    main()
