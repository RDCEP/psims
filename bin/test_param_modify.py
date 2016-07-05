#!/usr/bin/env python
import unittest
import param_modify
from collections import OrderedDict

class TestParamModify(unittest.TestCase):

    #
    # Deleting
    #
    def test_delete_scalar(self):
        data = OrderedDict()
        data['model'] = 'apsim'
        param_modify.del_value(data, ['model'], None)
        self.assertFalse('model' in data)

    def test_delete_entire_list(self):
        data = OrderedDict()
        data['fruits'] = ['apple', 'banana', 'orange']
        param_modify.del_value(data, ['fruits'], None)
        self.assertFalse('fruits' in data)

    def test_delete_zeroth(self):
        data = OrderedDict()
        data['fruits'] = ['apple', 'banana', 'orange']
        param_modify.del_value(data, ['fruits'], 0)
        self.assertEqual(['banana', 'orange'], data['fruits'])

    def test_delete_middle(self):
        data = OrderedDict()
        data['fruits'] = ['apple', 'banana', 'orange']
        param_modify.del_value(data, ['fruits'], 1)
        self.assertEqual(['apple', 'orange'], data['fruits'])

    def test_delete_last(self):
        data = OrderedDict()
        data['fruits'] = ['apple', 'banana', 'orange']
        param_modify.del_value(data, ['fruits'], 2)
        self.assertEqual(['apple', 'banana'], data['fruits'])

    def test_delete_entire_sublist(self):
        data = OrderedDict()
        data['foods'] = {}
        data['foods']['vegetables'] = ['carrots', 'corn']
        data['foods']['fruits'] = ['apple', 'banana', 'orange']
        param_modify.del_value(data, ['foods', 'fruits'], None)
        self.assertTrue('vegetables' in data['foods'])
        self.assertFalse('fruits' in data['foods'])

    def test_delete_item_sublist(self):
        data = OrderedDict()
        data['foods'] = {}
        data['foods']['vegetables'] = ['carrots', 'corn']
        data['foods']['fruits'] = ['apple', 'banana', 'orange']
        param_modify.del_value(data, ['foods', 'fruits'], 1)
        self.assertEqual(['apple', 'orange'], data['foods']['fruits'])
        self.assertEqual(['carrots', 'corn'], data['foods']['vegetables'])

    #
    # Adding / Setting
    #
    def test_add_scalar(self):
        data = OrderedDict()
        param_modify.set_scalar_value(data, ['model'], 'apsim')
        self.assertEqual(data['model'], 'apsim')

    def test_add_subscalar(self):
        data = OrderedDict()
        param_modify.set_scalar_value(data, ['model', 'type'], 'apsim')
        self.assertEqual(data['model']['type'], 'apsim')

    def test_add_list_item(self):
        data = OrderedDict()
        data['fruits'] = ['apple', 'orange']
        param_modify.set_list_value(data, ['fruits'], ['banana'], 0)
        self.assertEqual(data['fruits'], ['banana', 'orange'])

    def test_add_list_item_oob(self):
        data = OrderedDict()
        data['fruits'] = ['apple']
        param_modify.set_list_value(data, ['fruits'], ['orange'], 10)
        self.assertEqual(data['fruits'], ['apple', 'orange'])

    def test_add_list_undefined(self):
        data = OrderedDict()
        param_modify.set_list_value(data, ['fruits'], ['banana'], 0)
        self.assertEqual(data['fruits'], ['banana'])

    def test_add_list_undefined_oob(self):
        data = OrderedDict()
        param_modify.set_list_value(data, ['fruits'], ['banana'], 2)
        self.assertEqual(data['fruits'], ['banana'])

if __name__ == '__main__':
    unittest.main()
