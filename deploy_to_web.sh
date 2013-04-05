#!/usr/bin/env bash
[ -z $DB_HOST ] && echo Environment variable DB_HOST not set.&&exit 1
[ -z $DB_PASSWORD ] && echo Environmetn variable DB_PASSORD not set.&&exit 1
puppet = 'puppet'

function ec2_scp {
  scp -o StrictHostKeyChecking=no -i /var/go/infra_lab.pem $1 ubuntu@$2:
}

function ec2_ssh {
  ssh -o StrictHostKeyChecking=no -i /var/go/infra_lab.pem ubuntu@$1 $2
}

function vagrant_scp {
	# Vagrant boxes have puppet installed in /opt/vagrant_ruby/bin/puppet, but it's only added to the path in interactive shells.
	puppet = '/opt/vagrant_ruby/bin/puppet'
	[ ! -f ~/.ssh/vagrant ] && wget https://raw.github.com/mitchellh/vagrant/master/keys/vagrant&&mv ./vagrant ~/.ssh/&&chmod 600 ~/.ssh/vagrant
	scp -o StrictHostKeyChecking=no -i ~/.ssh/vagrant $1 vagrant@$2:
}

function vagrant_ssh {
	# Vagrant boxes have puppet installed in /opt/vagrant_ruby/bin/puppet, but it's only added to the path in interactive shells.
	puppet = '/opt/vagrant_ruby/bin/puppet'
	[ ! -f ~/.ssh/vagrant ] && wget https://raw.github.com/mitchellh/vagrant/master/keys/vagrant&&mv ./vagrant ~/.ssh/&&chmod 600 ~/.ssh/vagrant
    ssh -o StrictHostKeyChecking=no -i ~/.ssh/vagrant vagrant@$1 $2
}

# For EC2
# ec2_scp puppet.tgz webhost.name.amazon.com
# ec2_scp opencart.deb webhost.name.amazon.com

# ec2_ssh web.part2.com "tar zxvf puppet.tgz"
# ec2_ssh web.part2.com "sudo FACTER_database_host=$DB_HOST FACTER_database_password=$DB_PASSWORD puppet apply --modulepath=modules web.pp"

# For Vagrant
vagrant_scp puppet.tgz web
vagrant_scp opencart.deb web

vagrant_ssh web "tar zxvf puppet.tgz"
vagrant_ssh web "sudo FACTER_database_host=$DB_HOST FACTER_database_password=$DB_PASSWORD $puppet apply --modulepath=modules web.pp"
