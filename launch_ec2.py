#!/usr/bin/env python

import json, os, sys, socket
from time import sleep

import boto

AMI_ID="ami-06ad526f"
INSTANCE_TYPE="t1.micro"

USERNAME="ubuntu"

if not os.path.exists('data'):
    os.mkdir('data')

KEYPAIR_FILENAME = "data/keypair.pem"
INSTANCE_FILENAME = "data/instance.json"

SSH_FILENAME = "data/ec2_ssh"
SCP_FILENAME = "data/ec2_scp"
CUCUMBER_FILENAME = "data/ec2_cucumber"

def load_data():
    inp = open(INSTANCE_FILENAME, 'r')
    try:
        return json.load(inp)
    finally:
        inp.close()

def dump_data(instance, key_name, security_group):
    dns = instance.dns_name
    data  = { 'id' : instance.id,
              'dns' : dns,
              'key_name' : key_name,
              'security_group' : security_group }

    out = open(INSTANCE_FILENAME, 'w')
    json.dump(data, out)
    out.flush()
    out.close()
    os.chmod(INSTANCE_FILENAME, 0666)

    ssh_out = open(SSH_FILENAME, 'w')
    ssh_out.writelines([
            "#!/usr/bin/env bash\n",
            "\n",
            "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s %s@%s $*\n" % (KEYPAIR_FILENAME, USERNAME, dns),
            ])
    ssh_out.flush()
    ssh_out.close()
    os.chmod(SSH_FILENAME, 0755)

    scp_out = open(SCP_FILENAME, 'w')
    scp_out.writelines([
            "#!/usr/bin/env bash\n",
            "\n",
            "scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s $1 %s@%s:\n" % (KEYPAIR_FILENAME, USERNAME, dns),
            ])
    scp_out.flush()
    scp_out.close()
    os.chmod(SCP_FILENAME, 0755)

    cucumber_out = open(CUCUMBER_FILENAME, 'w')
    cucumber_out.writelines([
            "#!/usr/bin/env bash\n",
            "\n",
            "BASE_URL='http://%s' cucumber $*" % dns,
            ])
    cucumber_out.flush()
    cucumber_out.close()
    os.chmod(CUCUMBER_FILENAME, 0755)

def create_keypair(ec2, key_name):
    keypair = ec2.create_key_pair(key_name)
    out = open(KEYPAIR_FILENAME, 'w')
    out.write(keypair.material)
    out.flush()
    out.close()
    os.chmod(KEYPAIR_FILENAME, 0600)
    print "Saved keypair %s to %s" % (key_name, KEYPAIR_FILENAME)

def create_security_group(ec2, security_group):
    sg = ec2.create_security_group(security_group, "Puppet testing")
    sg.authorize(ip_protocol="tcp", from_port="22", to_port="22", cidr_ip="0.0.0.0/0")
    sg.authorize(ip_protocol="tcp", from_port="80", to_port="80", cidr_ip="0.0.0.0/0")
    print "Created security group named %s with ssh access" % security_group

def wait_for_instance(instance, temporary_state, final_state):
    print "Instance state is %s" % instance.state
    while instance.state == temporary_state:
        sleep(5)
        print "..." + instance.update()

    if instance.state != final_state:
        raise Exception("Final instance state is %s instead of %s" % (instance.state, final_state))
    else:
        print "..%s!" % instance.state
        return instance

def launch_instance(ec2, key_name, security_group):
    reservation = ec2.run_instances(image_id=AMI_ID,
                                    key_name=key_name,
                                    security_groups=[security_group],
                                    instance_type=INSTANCE_TYPE)

    instance = reservation.instances[0]
    print "Launched instance %s" % instance
    return wait_for_instance(instance, u"pending", u"running")

def create(ec2, key_name, security_group):
    create_keypair(ec2, key_name)
    create_security_group(ec2, security_group)
    return launch_instance(ec2, key_name, security_group)

def clean(ec2, instance_id, key_name, security_group):
    instance = ec2.get_all_instances(instance_ids=[instance_id])[0].instances[0]
    ec2.terminate_instances(instance_ids=[instance_id])
    wait_for_instance(instance, u"shutting-down", u"terminated")
    ec2.delete_key_pair(key_name)
    ec2.delete_security_group(security_group)
    os.remove(KEYPAIR_FILENAME)
    os.remove(INSTANCE_FILENAME)
    os.remove(SSH_FILENAME)
    os.remove(SCP_FILENAME)

def main(aws_access_key, aws_secret_key, revision, counter, mode):
    ec2 = boto.connect_ec2(aws_access_key, aws_secret_key)

    hostname = socket.gethostname()

    if mode == "start":
        key_name = "Go-%s-%s-%s-Key" % (revision, counter, hostname)
        security_group = "Go-%s-%s-%s-SG" % (revision, counter, hostname)
        instance = create(ec2, key_name, security_group)
        dump_data(instance, key_name, security_group)
    elif mode == "stop":
        data = load_data()
        clean(ec2, data['id'], data['key_name'], data['security_group'])
    else:
        raise Exception("Unknown mode %s" % mode)

def _usage():
    print "Usage: launch_ec2.py start|stop"
    sys.exit(10)

if __name__ == "__main__":
    aws_access_key = os.environ["AWS_ACCESS_KEY"]
    aws_secret_key = os.environ["AWS_SECRET_KEY"]

    go_revision = os.environ["GO_REVISION_BUILD-SCRIPTS"]
    pipeline_counter = os.environ["GO_PIPELINE_COUNTER"]

    if 'AMI_ID' in os.environ:
        AMI_ID = os.environ['AMI_ID']
    if 'INSTANCE_TYPE' in os.environ:
        INSTANCE_TYPE = os.environ['INSTANCE_TYPE']
    if 'USERNAME' in os.environ:
        USERNAME = os.environ['USERNAME']

    if len(sys.argv) < 2:
        _usage()
    else:
        mode = sys.argv[1]
        main(aws_access_key, aws_secret_key, go_revision, pipeline_counter, mode)
