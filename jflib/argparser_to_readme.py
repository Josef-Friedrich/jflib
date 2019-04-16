

def argparser_to_readme(argparser, template='README-template.md',
                        destination='README.md', indentation=0,
                        placeholder='{{ argparse }}'):
    """Add the formatted help output of a command line utility using the
    Python module `argparse` to a README file.

    :param object argparser: The argparse parser object.
    :param str template: The path of a template text file containing the
      placeholder. Default: `README-template.md`
    :param str destination: The path of the destination file. Default:
      `README.me`
    :param int indentation: Indent the formatted help output by X spaces.
      Default: 0
    :param str placeholder: Placeholder string that gets replaced by the
      formatted help output. Default: `{{ argparse }}`
    """
    help_string = argparser().format_help()

    if indentation > 0:
        indent_lines = []
        lines = help_string.split('\n')
        for line in lines:
            indent_lines.append(' ' * indentation + line)

        help_string = '\n'.join(indent_lines)

    with open(template, 'r', encoding='utf-8') as template_file:
        template_string = template_file.read()
        readme = template_string.replace(placeholder, help_string)

    readme_file = open(destination, 'w')
    readme_file.write(readme)
    readme_file.close()
