import json, os, sys
from time import sleep

import boto

AMI_ID="ami-06ad526f"
INSTANCE_TYPE="t1.micro"

KEYPAIR_FILENAME = "keypair.pem"
INSTANCE_FILENAME = "instance.json"

def load_data():
    inp = open(INSTANCE_FILENAME, 'r')
    try:
        return json.load(inp)
    finally:
        inp.close()

def dump_data(instance, keypair, security_group):
    data  = { 'id' : instance.id,
              'dns' : instance.dns_name,
              'keypair' : keypair,
              'security_group' : security_group }
    out = open(INSTANCE_FILENAME, 'w')
    json.dump(data, out)
    out.flush()
    out.close()

def create_keypair(ec2, keypair):
    keypair = ec2.create_key_pair(keypair)
    out = open(KEYPAIR_FILENAME, 'w')
    out.write(keypair.material)
    out.flush()
    out.close()
    print "Saved keypair %s to %s" % (keypair, KEYPAIR_FILENAME)

def create_security_group(ec2, security_group):
    sg = ec2.create_security_group(security_group, "Puppet testing")
    sg.authorize(ip_protocol="tcp", from_port="22", to_port="22", cidr_ip="0.0.0.0/0")
    print "Created security group named %s with ssh access" % security_group

def wait_for_instance(instance):
    print "Instance state is %s" % instance.state
    while instance.state == u'pending':
        print "..." + instance.update()
        sleep(5)

    print "Final instance state is %s" % instance.state
    return instance.state == u"running"

def launch_instance(ec2, keypair, security_group):
    reservation = ec2.run_instances(image_id=AMI_ID,
                                    key_name=keypair,
                                    security_groups=[security_group],
                                    instance_type=INSTANCE_TYPE)

    instance = reservation.instances[0]
    print "Launched instance %s" % instance
    return wait_for_instance(instance)

def create(aws_access_key, aws_secret_key, keypair, security_group):
    ec2 = boto.connect_ec2(aws_access_key, aws_secret_key)
    create_keypair(ec2, keypair)
    create_security_group(ec2, security_group)
    launch_instance(ec2, keypair, security_group)

def clean(ec2, instance_id, keypair, security_group):
    ec2.terminate_instancees(instance_ids=[instance_id])
    ec2.delete_key_pair(keypair)
    ec2.delete_security_group(security_group)

def main(aws_access_key, aws_secret_key, go_revision, pipeline_counter, mode):
    if mode == "create":
        keypair = "Go-%s-%s-Key" % (go_revision, pipeline_counter)
        security_group = "Go-%s-%s-SG" % (go_revision, pipeline_counter)
        create(aws_access_key, aws_secret_key, keypair, security_group)
    elif mode == "clean":
        data = load_data()
        clean(data['instance_id'], data['keypair'], data['security_group'])
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

    if len(sys.argv) < 2:
        _usage()
    else:
        mode = sys.argv[1]
            _usage()
