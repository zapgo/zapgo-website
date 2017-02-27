from invoke import task
import json
import yaml
import semver

import os


def format_yaml(template, config):
    # Replace in ${ENV_VAR} in template with value:
    formatted = template
    for k, v in config.items():
        formatted = formatted.replace('${%s}' % k, v)
    return formatted


@task
def templater(ctx, config, template='kubernetes/templates/all-in-one.yaml'):
    """ Creates deployment setup for given config file"""

    if config[-5:] != '.yaml':
        config += '.yaml'

    # Get path of tasks.py file to allow independence from CWD
    dir_path = os.path.dirname(os.path.realpath(__file__))

    if not os.path.isabs(config):
        config = os.path.join(dir_path, config)
    if not os.path.isabs(template):
        template = os.path.join(dir_path, template)

    with open(config, 'r') as stream:
        config_dict = yaml.load(stream)

    with open(template, 'r') as myfile:
        template_str = myfile.read()

    formatted = format_yaml(template_str, config_dict)
    output_dir = os.path.join(dir_path, 'kubernetes', config_dict['NAMESPACE'])
    output_path = os.path.join(output_dir, 'all-in-one.yaml')
    if os.path.isfile(output_path):
        print('Deployment config already exists. Aborting.')
    else:
        os.mkdir(output_dir)
        with open(output_path, 'w') as myfile:
            myfile.write(formatted)


@task
def build(ctx, tag):
    """
    Build project's docker image
    """
    cmd = 'docker build -t %s .' % tag
    ctx.run(cmd, echo=True)


@task
def run(ctx, image, port):
    """
    Run specified docker image on specified port
    """

    cmd = 'docker run -p {}:{} {}'.format(port, 80, image)
    ctx.run(cmd, echo=True)


def get_config(config):
    if config[-5:] != '.yaml':
        config += '.yaml'

    # Use /server as base path
    dir_path = os.path.dirname(os.path.realpath(__file__))
    server_dir_path = dir_path
    if not os.path.isabs(config):
        config = os.path.join(server_dir_path, config)

    with open(config, 'r') as stream:
        config_dict = yaml.load(stream)

    return config_dict


@task
def push(ctx, config, version_tag):
    """
    Build, tag and push docker image
    """
    config_dict = get_config(config)
    image_name = config_dict['IMAGE'].split(':')[0]
    image = '{}:{}'.format(image_name, version_tag)

    build(ctx, image)
    ctx.run('gcloud docker -- push %s' % image, echo=True)


@task
def version(ctx, bump='prerelease'):
    """
    Returns incremented version number by looking at git tags
    """
    # Get latest git tag:
    result = ctx.run('git tag --sort=-v:refname', hide='both')
    latest_tag = result.stdout.split('\n')[0][1:]

    increment = {'prerelease': semver.bump_prerelease,
                 'patch': semver.bump_patch,
                 'minor': semver.bump_minor,
                 'major': semver.bump_major}

    incremented = increment[bump](latest_tag)
    print(incremented)

    return incremented


@task
def release(ctx, config, version_bump='prerelease'):
    """
    Bump version, push git tag, push docker image
    N.B. Commit changes first
    """

    config_dict = get_config(config)

    bumped_version = version(ctx, bump=version_bump)
    tag = 'v' + bumped_version
    comment = 'Version ' + bumped_version

    # Create, tag and push docker image:
    image_name = config_dict['IMAGE'].split(':')[0]
    push(ctx, config, tag)

    # Create an push git tag:
    ctx.run("git tag '%s' -m '%s'" % (tag, comment), echo=True)
    ctx.run("git push origin %s" % tag, echo=True)

    print('Release Info:\n'
          'Tag: {}\n'
          'Image: {}\n'.format(tag, image_name))


@task
def deploy(ctx, config, version_tag):
    """
    Updates kubernetes deployment to use specified version
    """

    config_dict = get_config(config)

    image_name = config_dict['IMAGE'].split(':')[0]
    image = '{}:{}'.format(image_name, version_tag)

    ctx.run('kubectl set image deployment/{} '
            '{}={} --namespace={}'.format(config_dict['PROJECT_NAME'],
                                          config_dict['PROJECT_NAME'],
                                          image,
                                          config_dict['NAMESPACE']), echo=True)


@task
def live(ctx, config):
    """Checks which version_tag is live"""
    config_dict = get_config(config)

    result = ctx.run('kubectl get deployment/{} --output=json --namespace={}'.format(config_dict['PROJECT_NAME'],
                                                                                     config_dict['NAMESPACE']),
                     echo=True,
                     hide='stdout')

    server_config = json.loads(result.stdout)
    image = server_config['spec']['template']['spec']['containers'][0]['image']
    print(image)
    return image
