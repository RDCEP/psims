#!/usr/bin/env python
import argparse
import re
import sys
import ruamel.yaml

def del_value(dictionary, keys, index):
    for k in keys[:-1]:
        dictionary = dictionary[k]
    if index or index == 0:
        dictionary[keys[-1]].pop(index)
    else:
        del dictionary[keys[-1]]

def get_value(dictionary, keys):
    for k in keys:
        dictionary = dictionary[k]
    return dictionary

def set_scalar_value(dictionary, keys, value):
    for k in keys[:-1]:
        try:
            dictionary = dictionary[k]
        except KeyError:
            dictionary[k] = {}
            dictionary = dictionary[k]
    dictionary[keys[-1]] = value

def set_list_value(dictionary, keys, value, index):
    for k in keys[:-1]:
        try:
            dictionary = dictionary[k]
        except KeyError:
            dictionary[k] = {}
            dictionary = dictionary[k]
    try:
        dictionary[keys[-1]][index] = value
    except KeyError:
        dictionary[keys[-1]] = [value]
    except IndexError:
        dictionary[keys[-1]].append(value)

def recursive_replace(dictionary, old_str, new_str):
    new = {}
    for k, v in dictionary.iteritems():
        if isinstance(v, dict):
            v = recursive_replace(v, old_str, new_str)
            new[k] = v
        elif isinstance(v, str):
            new[k] = v.replace(old_str, new_str)
        else:
            new[k] = v
    return new

def str_to_num(s):
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s

def get_help():
    help = ('Examples:\n\n' +
           '# Add a parameter\n'
           './param_modify.py --input test --output test.out --action add --key model --value cenw\n\n'
           '# Delete a parameter\n'
           './param_modify.py --input test --output test.out --action delete --key postprocess\n\n'
           '# Rename a parameter\n'
           './param_modify.py --input test --output test.out --action rename --key model --value not_a_model\n\n'
           '# Replace string in all values\n'
           './param_modify.py --input test --output test.out --action replace_all --old oldstring --new newstring\n\n'
           '# Use : to represent levels of indentation\n'
           './param_modify.py --input test --output test.out --action add --key mygroup:myparam --value myvalue\n\n'
           '# Add item to element 2 of a list\n'
           './param_modify.py --input test --output test.out --action add --key mylist:2 --value myvalue\n\n'
           '# Another list example\n'
           './param_modify.py --input test --output test.out --action add --key mytranslator:mylist:2 --value myvalue\n\n')
    return help

def main():
    # Parse args
    parser = argparse.ArgumentParser(epilog=get_help(), formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--input', required=True, help='Input params file')
    parser.add_argument('--output', default=None, help='Output params file')
    parser.add_argument('--key', '--old', help='Key to replace')
    parser.add_argument('--value', '--new', help='New value')
    parser.add_argument('--action', choices=['add', 'delete', 'modify', 'rename', 'replace_all'], required=True, help='Which action to perform')
    options = parser.parse_args()

    keys       = options.key.split(':')
    index      = keys[-1]
    value      = str_to_num(options.value)
    inputfile  = options.input
    outputfile = options.output

    if type(str_to_num(index)) == int:
        index = str_to_num(keys.pop())
    else:
        index = None

    if not outputfile:
        outputfile = inputfile

    # Load yaml
    inputfile = open(inputfile)
    params = ruamel.yaml.load(inputfile, ruamel.yaml.RoundTripLoader)
    inputfile.close()

    # Handle actions
    if options.action == "add" or options.action == "modify":
        if index or index == 0:
            set_list_value(params, keys, value, index)
        else:
            set_scalar_value(params, keys, value)
    elif options.action == "add_list":
        set_list(params, keys, value)
    elif options.action == "delete":
        del_value(params, keys, index)
    elif options.action == "rename":
        old_value = get_value(params, keys)
        set_scalar_value(params, value, old_value, index)
        del_value(params, keys, index)
    elif options.action == "replace_all":
        params = recursive_replace(params, keys[0], value)

    # Save output
    outfile = open(outputfile, 'w')
    outfile.write(ruamel.yaml.dump(params, Dumper=ruamel.yaml.RoundTripDumper))
    outfile.close()

if __name__ == "__main__":
   main()
