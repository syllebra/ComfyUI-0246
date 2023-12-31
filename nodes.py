"""
@author: Trung0246
@title: ComfyUI-0246
@nickname: ComfyUI-0246
@description: Random nodes for ComfyUI I made to solve my struggle with ComfyUI (ex: pipe, process). Have varying quality.
"""

# Built-in
import sys
import ast
import random
import builtins
import json
import copy
import functools
import copy

# Self Code
from . import utils as lib0246

# 3rd Party
import aiohttp.web
import natsort

# ComfyUI
from server import PromptServer
import execution
import nodes

######################################################################################
######################################## IMPL ########################################
######################################################################################

def highway_impl(_prompt, _id, _workflow, _way_in, flag, kwargs):
	if isinstance(_prompt, list):
		_prompt = _prompt[0]
	if isinstance(_id, list):
		_id = _id[0]
	if isinstance(_workflow, list):
		_workflow = _workflow[0]

	if isinstance(_way_in, list):
		_way_in = _way_in[0]

	if _way_in is None:
		_way_in = lib0246.RevisionDict()
	else:
		_way_in = lib0246.RevisionDict(_way_in)

	# _way_in._id = _id
	# _way_in.purge(_way_in.find(lambda item: item.id == _id))

	# Time to let the magic play out
		
	curr_node = next(_ for _ in _workflow["workflow"]["nodes"] if str(_["id"]) == _id)

	for i, curr_input in enumerate(curr_node["inputs"]):
		if curr_input["name"] in kwargs:
			name = _workflow["workflow"]["extra"]["0246.__NAME__"][_id]["inputs"][str(i)]["name"][1:]
			if flag:
				_way_in[("data", name)] = lib0246.RevisionBatch(*kwargs[curr_input["name"]])
			else:
				_way_in[("data", name)] = kwargs[curr_input["name"]]
			_way_in[("type", name)] = curr_input["type"]

	res = []

	for i, curr_output in enumerate(curr_node["outputs"]):
		if curr_output.get("links") and curr_output["name"] not in lib0246.BLACKLIST:
			name = _workflow["workflow"]["extra"]["0246.__NAME__"][_id]["outputs"][str(i)]["name"][1:]
			if ("data", name) in _way_in:
				if curr_output["type"] == "*" or curr_output["type"] == _way_in[("type", name)]:
					res.append(_way_in[("data", name)])
				else:
					raise Exception(f"Output \"{name}\" is not defined or is not of type \"{curr_output['type']}\". Expected \"{_way_in[('type', name)]}\".")

	_way_in[("kind")] = "highway"
	_way_in[("id")] = _id

	return (_way_in, ) + tuple(res)

def gather_highway_impl(_dict_list, _id):
	new_dict = lib0246.RevisionDict()

	if _dict_list is None:
		return new_dict
	
	if isinstance(_id, list):
		_id = _id[0]
	
	for elem in _dict_list:
		iter_inst = elem.path_iter(("data", ))
		for key in iter_inst:
			if ("type", key[1]) not in new_dict:
				new_dict[("type", key[1])] = elem[("type", key[1])]
			if ("data", key[1]) not in new_dict:
				new_dict[("data", key[1])] = lib0246.RevisionBatch()
			if isinstance(elem[("data", key[1])], lib0246.RevisionBatch):
				new_dict[("data", key[1])].extend(elem[("data", key[1])])
			else:
				new_dict[("data", key[1])].append(elem[("data", key[1])])

	new_dict[("kind")] = "highway"
	new_dict[("id")] = _id

	return new_dict

def junction_impl(self, _id, _prompt, _workflow, _junc_in, _offset = None, _in_mode = False, _out_mode = False, _offset_mode = False, **kwargs):
	if isinstance(_prompt, list):
		_prompt = _prompt[0]
	if isinstance(_id, list):
		_id = _id[0]
	if isinstance(_offset, list):
		_offset = _offset[0]
	if isinstance(_workflow, list):
		_workflow = _workflow[0]

	if _junc_in is None:
		_junc_in = lib0246.RevisionDict()
	else:
		_junc_in = lib0246.RevisionDict(_junc_in)

	# _junc_in._id = _id
	# _junc_in.purge(_junc_in.find(lambda item: item.id == _id))

	# Pack all data from _junc_in and kwargs together with a specific format
		
	curr_node = next(_ for _ in _workflow["workflow"]["nodes"] if str(_["id"]) == _id)

	if _in_mode:
		flat_iter = lib0246.FlatIter(kwargs)
		for param, (key, value) in lib0246.flat_zip(list(filter(lambda _: _["name"] not in lib0246.BLACKLIST, curr_node["inputs"])), flat_iter):
			junction_pack_loop(_junc_in, param["type"], value)
	else:
		for param, key in zip(list(filter(lambda _: _["name"] not in lib0246.BLACKLIST, curr_node["inputs"])), list(kwargs)):
			junction_pack_loop(_junc_in, param["type"], kwargs[key])

	# Parse the offset string

	if hasattr(self, "_prev_offset") and hasattr(self, "_parsed_offset") and _offset is not None:
		if type(_offset) is str:
			_offset = ast.literal_eval(_offset)
		if _offset["data"] != self._prev_offset:
			parsed_offset, err = lib0246.parse_offset(_offset["data"])
			if err:
				raise Exception(err)
			self._prev_offset = _offset["data"]
			self._parsed_offset = parsed_offset

	# Apply the offset to the junction input

	if hasattr(self, "_parsed_offset"):
		if self._parsed_offset is None:
			raise Exception("Offset is not parsed.")
		
		for elem in self._parsed_offset:
			total = _junc_in.path_count(("data", elem[0]))
			if total == 0:
				raise Exception(f"Type \"{elem[0]}\" in offset string does not available in junction.")

			# Check for ops char

			if elem[1][0] == '+':
				_junc_in[("index", elem[0])] += int(elem[1][1:])
			elif elem[1][0] == '-':
				_junc_in[("index", elem[0])] -= int(elem[1][1:])
			else:
				_junc_in[("index", elem[0])] = int(elem[1])
			
			temp = _junc_in[("index", elem[0])]
			if temp >= total:
				raise Exception(f"Offset \"{elem[1]}\" (total: \"{temp}\") is too large (count: \"{total}\").")
			elif temp < 0:
				raise Exception(f"Offset \"{elem[1]}\" (total: \"{temp}\") is too small (count: \"{total}\").")

	res = []
	track = {}

	if _out_mode:
		done_type = {}
		for elem in curr_node["outputs"]:
			if elem["name"] in lib0246.BLACKLIST:
				continue

			if elem["type"] in done_type:
				# Rotate the list from [11, 22, 33] to [22, 33, 11]
				res.append(done_type[elem["type"]][1:] + done_type[elem["type"]][:1])
				continue
			
			total = _junc_in.path_count(("data", elem["type"]))
			if total == 0:
				raise Exception(f"Type \"{elem['type']}\" of output \"{elem['name']}\" does not available in junction.")
			
			offset = _junc_in[("index", elem["type"])]

			if offset >= total:
				raise Exception(f"Too much type \"{elem['type']}\" being taken or offset \"{offset}\" is too large (count: \"{total}\").")
			
			temp = []
			res.append(temp)

			for i in range(offset, total):
				temp.append(_junc_in[("data", elem["type"], i)])

			done_type[elem["type"]] = temp
		
		# Check if every single array in done_type have same length
		base_len = -1
		base_type = None
		for key in done_type:
			curr_len = len(done_type[key])
			if base_len == -1:
				base_len = curr_len
				base_type = key
			elif curr_len != base_len:
				print("\033[93m" + f"{lib0246.HEAD_LOG}WARNING: Type \"{key}\" has different amount (node {_id}, got {curr_len}, want {base_len} from first type \"{base_type}\")." + "\033[0m")
	else:
		for key in _junc_in.path_iter(("type", )):
			track[key[1]] = 0

		for elem in curr_node["outputs"]:
			if elem["name"] in lib0246.BLACKLIST:
				continue

			total = _junc_in.path_count(("data", elem["type"]))
			if total == 0:
				raise Exception(f"Type \"{elem['type']}\" of output \"{elem['name']}\" does not available in junction.")
			
			offset = _junc_in[("index", elem["type"])]
			real_index = track[elem["type"]] + offset

			if real_index >= total:
				raise Exception(f"Too much type \"{elem['type']}\" being taken or offset \"{offset}\" is too large (count: \"{total}\").")
			
			res.append(_junc_in[("data", elem["type"], real_index)])
			track[elem["type"]] += 1

	_junc_in[("kind")] = "junction"
	_junc_in[("id")] = _id
	
	return (_junc_in, ) + tuple(res)

def gather_junction_impl(_dict_list, _id):
	new_dict = lib0246.RevisionDict()

	if _dict_list is None:
		return new_dict
	
	if isinstance(_id, list):
		_id = _id[0]
		
	for _dict in _dict_list:
		for tuple_key in _dict.path_iter(("data", )):
			junction_pack_loop(new_dict, tuple_key[1], _dict[tuple_key])

	new_dict[("kind")] = "junction"
	new_dict[("id")] = _id

	return new_dict

def junction_unpack(
		data_dict, param_dict, key_list,
		base_dict = {}, type_dict = {}, key_special=("default", "data", "index"),
		pack_func=lambda _: _, type_func=lambda _: _,
		fill_func=lambda d, k, v: d.setdefault(k, v)
	):

	for key in data_dict:
		if key[0] == key_special[2]:
			type_dict[type_func(key[1])] = data_dict[key]

	for elem in key_list:
		for param_key in param_dict[elem]:
			data_type = param_dict[elem][param_key][0]
			type_dict.setdefault(type_func(data_type), 0)

	for elem in key_list:
		for param_key in param_dict[elem]:
			param_tuple = param_dict[elem][param_key]
			defaults = {} if len(param_tuple) == 1 else param_tuple[1]
			data_key = (key_special[1], type_func(param_tuple[0]), type_dict.get(type_func(param_tuple[0]), 0))
			value = data_dict.get(data_key, defaults.get(key_special[0], None))
			fill_func(base_dict, param_key, pack_func(value))
			type_dict[type_func(param_tuple[0])] += 1

	return base_dict

def update_hold_db(key, data):
	if data is not None:
		Hold.HOLD_DB[key]["data"].extend(data)
	return [None] if not Hold.HOLD_DB[key]["data"] else Hold.HOLD_DB[key]["data"]

def junction_pack_loop(_junc_in, name, value):
	_junc_in[("type", name)] = type(value).__name__
	count = _junc_in.path_count(("data", name))
	_junc_in[("data", name, count)] = value
	if count == 0:
		_junc_in[("index", name)] = 0

def trace_node(_prompt, _id, _workflow, _shallow = False, _input = False):
	id_stk = []
	if _input:
		for key in _prompt[_id]["inputs"]:
			if isinstance(_prompt[_id]["inputs"][key], list) and key != "_event":
				id_stk.append(_prompt[_id]["inputs"][key][0])
	else:
		id_stk.append(_id)

	id_res = set()
	
	while len(id_stk) > 0:
		curr_id = id_stk.pop(0)
		if curr_id not in id_res:
			id_res.add(curr_id)
			for node in _workflow["workflow"]["nodes"]:
				if node["id"] == int(curr_id):
					if node.get("outputs"):
						for output in node["outputs"]:
							if output.get("links"):
								for link in output["links"]:
									linked_node_id = find_input_node(_workflow["workflow"]["nodes"], link)
									if linked_node_id is not None:
										if _shallow:
											if linked_node_id in BASE_EXECUTOR.outputs:
												del BASE_EXECUTOR.outputs[linked_node_id]
										else:
											id_stk.append(str(linked_node_id))

	return id_res

def find_input_node(nodes, link):
	for node in nodes:
		if node.get("inputs"):
			for input in node["inputs"]:
				if input["link"] == link:
					return node["id"]
	return None

class ScriptData(dict):
	def __init__(self, data):
		super().__init__(data)

def plan_exec_node(script, pin, **kwargs):
	func = getattr(script[("script", "node", "inst")], getattr(script[("script", "node", "class")], "FUNCTION"))
	if hasattr(script[("script", "node", "class")], "INPUT_IS_LIST") and script[("script", "node", "class")].INPUT_IS_LIST:
		return lib0246.transpose(func(**pin), tuple)
	else:
		return func(**pin)

def plan_rule_slice(func, res, pin, **kwargs):
	return res.extend(func(pin=curr_pin) for curr_pin in lib0246.dict_slice(pin))

def plan_rule_product(func, res, pin, **kwargs):
	return res.extend(func(pin=curr_pin) for curr_pin in lib0246.dict_product(pin))

def plan_rule_direct(func, res, pin, **kwargs):
	return res.extend(func(pin=pin))

########################################################################################
######################################## HIJACK ########################################
########################################################################################

PROMPT_COUNT = 0
PROMPT_ID = None
PROMPT_EXTRA = None

def execute_param_handle(*args, **kwargs):
	global PROMPT_ID
	global PROMPT_COUNT
	if PROMPT_ID is None or PROMPT_ID != args[2]:
		PROMPT_COUNT += 1
		PROMPT_ID = args[2]
		PROMPT_EXTRA = args[3]

	# for node_id in args[1]:
	# 	if node_id in RandomInt.RANDOM_DB:
	# 		del RandomInt.RANDOM_DB[node_id]

	return tuple(), {}

lib0246.hijack(execution.PromptExecutor, "execute", execute_param_handle)

def init_executor_param_handle(*args, **kwargs):
	return tuple(), {}

BASE_EXECUTOR = None

def init_executor_res_handle(result, *args, **kwargs):
	if not hasattr(args[0], lib0246.WRAP_DATA):
		global BASE_EXECUTOR
		if BASE_EXECUTOR is None:
			BASE_EXECUTOR = args[0]
	return result

lib0246.hijack(execution.PromptExecutor, "__init__", init_executor_param_handle, init_executor_res_handle)

COND_EXEC = [] # List of functions

# Just in case if we needs this ever again
def execute_node_param_handle(*args, **kwargs):
	return tuple(), {}

def execute_node_res_handle(result, *args, **kwargs):
	global COND_EXEC

	for curr_id in COND_EXEC:
		result.insert(0, (0, curr_id))

	return result

lib0246.hijack(builtins, "sorted", execute_node_param_handle, None, None, execution)

# NODE_INPUT_KEYS = ["required", "optional"]
# NODE_TYPES = ["_"]

def init_extension_param_handle(*args, **kwargs):
	return tuple(), {}

def init_extension_res_handle(result, *args, **kwargs):
	global NODE_INPUT_KEYS
	global NODE_TYPES
	# [TODO] Debug NODE_TYPES on why it have empty data
	# NODE_TYPES.extend(set([x for key in NODE_INPUT_KEYS
	# 	for y in [list(nodes.NODE_CLASS_MAPPINGS[node_class].INPUT_TYPES().get(key, {}).keys())
	# 		for node_class in nodes.NODE_CLASS_MAPPINGS]
	# 	for x in y]))
	return result

lib0246.hijack(nodes, "init_custom_nodes", init_extension_param_handle, init_extension_res_handle)

#####################################################################################
######################################## API ########################################
#####################################################################################

@PromptServer.instance.routes.post('/0246-parse')
async def parse_handler(request):
	data = await request.json()

	# Validate json
	if data.get("input") is None:
		return aiohttp.web.json_response({
			"error": ["No input provided"]
		})

	# Parse the input string
	expr_res, order, errors = lib0246.parse_query(data["input"], lib0246.HIGHWAY_OPS)

	lib0246.highway_check(expr_res, errors)

	# Return a JSON response with the processed data
	return aiohttp.web.json_response({
		"expr": expr_res,
		"order": order,
		"error": errors
	})

######################################################################################
######################################## NODE ########################################
######################################################################################

class Highway:
	@classmethod
	def INPUT_TYPES(s):
		return {
			"required": {
				"_query": ("STRING", {
					"default": ">data; <data",
					"multiline": False
				}),
			},
			"optional": {
				"_way_in": ("HIGHWAY_PIPE", ),
			},
			"hidden": {
				"_prompt": "PROMPT",
				"_id": "UNIQUE_ID",
				"_workflow": "EXTRA_PNGINFO" # Unfortunately EXTRA_PNGINFO does not get exposed during IS_CHANGED
			}
		}

	# Amogus moment ඞ
	RETURN_TYPES = lib0246.ByPassTypeTuple(("HIGHWAY_PIPE", ))
	RETURN_NAMES = lib0246.ByPassTypeTuple(("_way_out", ))
	FUNCTION = "execute"
	CATEGORY = "0246"

	# [TODO] Potential recursion error when attempting to hook the inout in not a very specific way
		# => May have to keep a unique identifier for each class and each node instance
			# Therefore if already exist then throw error
				# => Cyclic detection in JS instead of python

	# Do not remove the "useless" _query parameter, since data need to be consumed for expanding
	def execute(self, _id = None, _prompt = None, _workflow = None, _way_in = None, _query = None, **kwargs):
		return highway_impl(_prompt, _id, _workflow, _way_in, False, kwargs)
	
	@classmethod
	def IS_CHANGED(self, _query, _id = None, _prompt = None, _workflow = None, _way_in = None, *args, **kwargs):
		return lib0246.check_update(_query)

######################################################################################

class HighwayBatch:
	@classmethod
	def INPUT_TYPES(s):
		return {
			"required": {
				"_query": ("STRING", {
					"default": ">data; <data",
					"multiline": False
				}),
			},
			"optional": {
				"_way_in": ("HIGHWAY_PIPE", ),
			},
			"hidden": {
				"_prompt": "PROMPT",
				"_id": "UNIQUE_ID",
				"_workflow": "EXTRA_PNGINFO"
			}
		}

	RETURN_TYPES = lib0246.ByPassTypeTuple(("HIGHWAY_PIPE", ))
	RETURN_NAMES = lib0246.ByPassTypeTuple(("_way_out", ))
	INPUT_IS_LIST = True
	OUTPUT_IS_LIST = lib0246.TautologyRest()
	FUNCTION = "execute"
	CATEGORY = "0246"

	def execute(self, _id = None, _prompt = None, _workflow = None, _way_in = None, _query = None, **kwargs):
		return highway_impl(_prompt, _id, _workflow, gather_highway_impl(_way_in, _id), True, kwargs)
	
	@classmethod
	def IS_CHANGED(self, _query, _id = None, _prompt = None, _workflow = None, _way_in = None, *args, **kwargs):
		return lib0246.check_update(_query)

######################################################################################

class Junction:
	@classmethod
	def INPUT_TYPES(s):
		return {
			"required": {
				"_offset": ("STRING", {
					"default": ";",
					"multiline": False
				}),
				# "_mode": (["named_type", "internal_type"],),
			},
			"optional": {
				"_junc_in": ("JUNCTION_PIPE", ),
			},
			"hidden": {
				"_prompt": "PROMPT",
				"_id": "UNIQUE_ID",
				"_workflow": "EXTRA_PNGINFO"
			}
		}
	
	RETURN_TYPES = lib0246.ByPassTypeTuple(("JUNCTION_PIPE", ))
	RETURN_NAMES = lib0246.ByPassTypeTuple(("_junc_out", ))
	FUNCTION = "execute"
	CATEGORY = "0246"

	def __init__(self):
		self._prev_offset = None
		self._parsed_offset = None

	def execute(self, _id = None, _prompt = None, _workflow = None, _junc_in = None, _offset = None, **kwargs):
		return junction_impl(self, _id, _prompt, _workflow, _junc_in, _offset, **kwargs)
	
	@classmethod
	def IS_CHANGED(self, _offset, _id = None, _prompt = None, _workflow = None, _junc_in = None, *args, **kwargs):
		return lib0246.check_update(_offset)

######################################################################################

class JunctionBatch:
	@classmethod
	def INPUT_TYPES(s):
		return {
			"required": {
				"_offset": ("STRING", {
					"default": ";",
					"multiline": False
				}),
				"_mode": (["pluck", "batch"], ),
			},
			"optional": {
				"_junc_in": ("JUNCTION_PIPE", ),
			},
			"hidden": {
				"_prompt": "PROMPT",
				"_id": "UNIQUE_ID",
				"_workflow": "EXTRA_PNGINFO"
			}
		}
	
	RETURN_TYPES = lib0246.ByPassTypeTuple(("JUNCTION_PIPE", ))
	RETURN_NAMES = lib0246.ByPassTypeTuple(("_junc_out", ))
	INPUT_IS_LIST = True
	FUNCTION = "execute"
	CATEGORY = "0246"

	def __init__(self):
		self._prev_offset = None
		self._parsed_offset = None

	def execute(self, _id = None, _prompt = None, _workflow = None, _junc_in = None, _offset = None, _mode = None, **kwargs):
		if isinstance(_mode, list):
			_mode = _mode[0]

		# Why not adding extra combos to manage _in_mode, _out_mode, and _offset_mode?
			# To prevent people being stupid and we force them to use correct combination

		if _mode == "batch":
			setattr(JunctionBatch, "OUTPUT_IS_LIST", lib0246.TautologyRest())
			return junction_impl(self, _id, _prompt, _workflow, gather_junction_impl(_junc_in, _id), _offset, _in_mode = True, _out_mode = True, _offset_mode = True, **kwargs)
		else:
			try:
				delattr(JunctionBatch, "OUTPUT_IS_LIST")
			except AttributeError:
				pass
			return junction_impl(self, _id, _prompt, _workflow, gather_junction_impl(_junc_in, _id), _offset, _in_mode = True, _out_mode = False, **kwargs)

	@classmethod
	def IS_CHANGED(self, _id = None, _prompt = None, _workflow = None, _offset = None, _junc_in = None, _mode = None, *args, **kwargs):
		return lib0246.check_update(_offset)

######################################################################################

class Count:
	@classmethod
	def INPUT_TYPES(s):
		return {
			"required": {
				"_node": lib0246.ByPassTypeTuple(("*", )),
				"_event": ("STRING", {
					"default": "10",
					"multiline": False
				}),
			},
			"hidden": {
				"_id": "UNIQUE_ID"
			}
		}
	
	COUNT_DB = {}
	COUNT_ID = 0
	
	RETURN_TYPES = ("INT", "EVENT_TYPE")
	RETURN_NAMES = ("_count_int", "_count_event")
	INPUT_IS_LIST = True
	FUNCTION = "execute"
	CATEGORY = "0246"

	def execute(self, _id = None, _node = None, _event = None, **kwargs):
		global PROMPT_ID
		if Count.COUNT_ID != PROMPT_ID:
			Count.COUNT_DB = {}
			Count.COUNT_ID = PROMPT_ID
		if _id[0] not in Count.COUNT_DB:
			Count.COUNT_DB[_id[0]] = 0
		temp = Count.COUNT_DB[_id[0]]
		Count.COUNT_DB[_id[0]] += 1

		return {
			"ui": {
				"text": [f"Count: {temp}, Track: {Count.COUNT_ID}"]
			},
			"result": (temp, {
				"data": {
					"id": _id[0],
				},
				"bool": temp >= int(_event[0]),
			})
		}

######################################################################################

class RandomInt:
	@classmethod
	def INPUT_TYPES(s):
		# Random uint64 int
		return {
			"required": {
				"val": ("STRING", {
					"default": "rand,0",
					"multiline": False
				}),
				"min": ("INT", {
					"default": 0,
					"min": -9007199254740991,
					"max": 9007199254740991
				}),
				"max": ("INT", {
					"default": 9007199254740991,
					"min": -9007199254740991,
					"max": 9007199254740991
				}),
				"batch_size": ("INT", {
					"default": 2,
					"min": 1,
					"max": sys.maxsize
				}),
				"mode": (["usual", "keep", "force"], )
			},
			"optional": {
				"seed": ("INT", {
					"default": 0,
					"min": -1125899906842624,
					# "max": 18446744073709551615
					"max": 1125899906842624
				}),
			},
			"hidden": {
				"_id": "UNIQUE_ID"
			}
		}

	RANDOM_DB = {}
	
	RETURN_TYPES = ("INT", )
	RETURN_NAMES = ("rand_int", )
	INPUT_IS_LIST = True
	OUTPUT_IS_LIST = (True, )
	FUNCTION = "execute"
	CATEGORY = "0246"

	def execute(self, _id = None, val = None, min = None, max = None, seed = None, batch_size = None, mode = None, **kwargs):
		if min[0] > max[0]:
			raise Exception("Min is greater than max.")
		
		if _id[0] not in RandomInt.RANDOM_DB:
			RandomInt.RANDOM_DB[_id[0]] = {
				"track": None,
				"prev": [],
				"prev_batch_size": 0,
				"inst": random.Random(),
				"seed": seed[0],
				"flag": 0
			}

		db = RandomInt.RANDOM_DB[_id[0]]

		if db["track"] != PROMPT_ID:
			db["track"] = PROMPT_ID
			db["flag"] = 0
			if mode[0] == "keep" or db["prev_batch_size"] != batch_size[0]:
				db["prev"].clear()
				db["prev_batch_size"] = 0
				mode[0] = "force"

		raw: list = val[0].split(",")
		if len(raw) > batch_size[0]:
			raw = raw[:batch_size[0]]

		for i in range(len(raw)):
			raw[i] = raw[i].strip()
			if raw[i].isnumeric():
				lib0246.append_replace(db["prev"], i, int(raw[i]))
			else:
				if db["prev_batch_size"] != len(raw) or len(raw) <= i or raw[i] == "rand":
					if seed[0] != db["seed"] or mode[0] == "force":
						db["inst"].seed(seed[0])
						db["seed"] = seed[0]
						mode[0] = ""
					lib0246.append_replace(db["prev"], i, db["inst"].randint(min[0], max[0]))
				elif raw[i] == "add":
					if mode[0] != "force" or (db["flag"] < 1 and mode[0] == "force"):
						db["prev"][i] += 1
				elif raw[i] == "sub":
					if mode[0] != "force" or (db["flag"] < 1 and mode[0] == "force"):
						db["prev"][i] -= 1
				else:
					raise Exception(f"Invalid value \"{raw[i]}\".")

		db["prev_batch_size"] = len(raw)
		db["flag"] += 1

		msg = f"Value: {{{', '.join([str(x) for x in db['prev']])}}}, " + \
			f"Seed: {db['seed']}, " + \
			f"Track: {PROMPT_ID}"

		return {
			"ui": {
				"text": [msg]
			},
			"result": [copy.copy(db["prev"])]
		}
	
	@classmethod
	def IS_CHANGED(self, val = None, min = None, max = None, batch_size = None, *args, **kwargs):
		return float("NaN")

######################################################################################

class Hold:
	@classmethod
	def INPUT_TYPES(s):
		return {
			"required": {
				"_mode": (["keep", "save", "clear", "ignore"], ),
				"_key_id": ("STRING", {
					"default": "",
					"multiline": False
				}),
			},
			"optional": {
				"_data_in": lib0246.ByPassTypeTuple(("*", )),
				"_hold": ("HOLD_TYPE", )
			},
			"hidden": {
				"_id": "UNIQUE_ID"
			}
		}
	
	HOLD_DB = {}
	
	RETURN_TYPES = lib0246.ByPassTypeTuple(("*", ))
	RETURN_NAMES = ("_data_out", )
	INPUT_IS_LIST = True
	OUTPUT_IS_LIST = lib0246.TautologyAll()
	FUNCTION = "execute"
	CATEGORY = "0246"

	def execute(self, _data_in = None, _id = None, _hold = None, _mode = None, _key_id = None, **kwargs):
		mode = _mode[0] if _mode else None

		if _id[0] not in Hold.HOLD_DB:
			Hold.HOLD_DB[_id[0]] = {
				"track": PROMPT_ID,
				"data": []
			}

		if Hold.HOLD_DB[_id[0]]["track"] != PROMPT_ID:
			Hold.HOLD_DB[_id[0]]["track"] = PROMPT_ID

			if mode != "save":
				Hold.HOLD_DB[_id[0]]["data"] = []

		ui_text = f"Id: {_id[0]}, "

		# Check if _key_id is specified and process accordingly
		if _key_id and len(_key_id[0]) > 0:
			if mode == "clear":
				Hold.HOLD_DB[_key_id[0]]["data"] = []
			result = update_hold_db(_key_id[0], _data_in)
			ui_text += f"Size: {lib0246.len_zero_arr(result)}, Key: {_key_id[0]}, "
		# Check if _hold is specified and process accordingly
		elif _hold and _hold[0]:
			result = _data_in if _data_in is not None else [None]
			ui_text += f"Size: {lib0246.len_zero_arr(result)}, Passed, "
		else:
			# Update the outputs and HOLD_DB for _id if specified
			if _id:
				result = update_hold_db(_id[0], None if (mode == "ignore" and len(Hold.HOLD_DB[_id[0]]["data"]) > 0) else _data_in)
				BASE_EXECUTOR.outputs[_id[0]] = Hold.HOLD_DB[_id[0]]["data"]
				ui_text += f"Size: {len(result)}, "
				if mode == "clear":
					Hold.HOLD_DB[_id[0]]["data"] = []
			else:
				ui_text += f"None, "
				result = [None]

		ui_text += f"Track: {Hold.HOLD_DB[_id[0]]['track']}"

		return {
			"ui": {
				"text": [ui_text]
			},
			"result": [result]
		}

######################################################################################

class Loop:
	@classmethod
	def INPUT_TYPES(s):
		return {
			"required": {
				"_event": ("EVENT_TYPE", ),
				"_mode": (["sweep"], ), # Reserved
				"_update": ("STRING", {
					"default": "{'update': ''}",
					"multiline": False
				}),
			},
			"hidden": {
				"_prompt": "PROMPT",
				"_id": "UNIQUE_ID",
				"_workflow": "EXTRA_PNGINFO"
			}
		}
	
	RETURN_TYPES = ("HOLD_TYPE", )
	RETURN_NAMES = ("_hold", )
	INPUT_IS_LIST = True
	FUNCTION = "execute"
	CATEGORY = "0246"

	LOOP_DB = {}

	def execute(self, _id = None, _prompt = None, _workflow = None, _event = None, _mode = None, _update = None, **kwargs):
		global BASE_EXECUTOR
		global PROMPT_ID
		if not _event[0]["bool"]:

			# [TODO] Less shitty way to remove _event from inputs
			try:
				del BASE_EXECUTOR.outputs[_prompt[0][_id[0]]["inputs"]["_event"][0]]
			except KeyError:
				pass

			if _mode[0] == "sweep":
				if (PROMPT_ID, _id[0]) in Loop.LOOP_DB:
					Loop.LOOP_DB[(PROMPT_ID, _id[0])]["count"] += 1
					for curr_id in Loop.LOOP_DB[(PROMPT_ID, _id[0])]["exec"]:
						if curr_id in BASE_EXECUTOR.outputs:
							del BASE_EXECUTOR.outputs[curr_id]
				else:
					# Not the most efficient. The better way is to find all nodes that are connected to inputs and this loop node
					Loop.LOOP_DB[(PROMPT_ID, _id[0])] = {
						"count": 1,
						"exec": trace_node(_prompt[0], _id[0], _workflow[0], _shallow = False, _input = True) # , lambda curr_id: exec.append(curr_id) if curr_id not in exec else None)
					}
					while Loop.LOOP_DB[(PROMPT_ID, _id[0])]["count"] > 0:
						Loop.LOOP_DB[(PROMPT_ID, _id[0])]["count"] -= 1
						for curr_id in Loop.LOOP_DB[(PROMPT_ID, _id[0])]["exec"]:
							if curr_id in BASE_EXECUTOR.outputs:
								del BASE_EXECUTOR.outputs[curr_id]
						success, error, ex = execution.recursive_execute(PromptServer.instance, _prompt[0], BASE_EXECUTOR.outputs, _id[0], {"extra_pnginfo": _workflow[0]}, set(), PROMPT_ID, BASE_EXECUTOR.outputs_ui, BASE_EXECUTOR.object_storage)
						if success is not True:
							raise ex
					del Loop.LOOP_DB[(PROMPT_ID, _id[0])]

		return (True, )

	@classmethod
	def IS_CHANGED(self, _update = None, _event = None, _mode = None, _id = None, _prompt = None, _workflow = None, *args, **kwargs):
		return lib0246.check_update(_update)

######################################################################################

class Merge:
	@classmethod
	def INPUT_TYPES(s):
		return {
			"required": {
				"_mode": (["flat", "deep"], ),
				"_pad": ("STRING", {
					"default": "_",
					"multiline": False
				}, )
			},
		}
	
	RETURN_TYPES = lib0246.ByPassTypeTuple(("HIGHWAY_PIPE", "JUNCTION_PIPE", "*", ))
	RETURN_NAMES = ("_way_out", "_junc_out", "_batch_out")
	INPUT_IS_LIST = True
	OUTPUT_IS_LIST = (False, False, True)
	FUNCTION = "execute"
	CATEGORY = "0246"

	def execute(self, _pad = None, _mode = None, **kwargs):
		way = None
		junc = None
		batch = []
		batch_count = 0

		for key in kwargs:
			for i in range(len(kwargs[key])):
				curr = kwargs[key][i]

				if isinstance(curr, list):
					if _mode[0] == "deep":
						batch.extend(curr)
						batch_count += len(curr)
					else:
						batch.append(curr)
						batch_count += 1
				elif isinstance(curr, lib0246.RevisionDict):
					if curr[("kind")] == "junction":
						if junc is None:
							junc = lib0246.RevisionDict()
							junc[("kind")] = "junction"
							junc[("id")] = curr[("id")]
						for type_name in curr.path_iter(("type", )):
							total = junc.path_count(("data", type_name[1]))
							for i in range(curr.path_count(("data", type_name[1]))):
								junc[("data", type_name[1], total + i)] = curr[("data", type_name[1], i)]
							junc[("index", type_name[1])] = 0
							junc[("type", type_name[1])] = type(curr[("data", type_name[1], 0)]).__name__
					else:
						if way is None:
							way = lib0246.RevisionDict()
							way[("kind")] = "highway"
							way[("id")] = curr[("id")]
						for key_name in curr.path_iter(("type", )):
							real_key = key_name[1]
							while True:
								if ("data", real_key) not in way:
									# way[("type", real_key)] = type(curr[("data", key_name[1])]).__name__
									way[("type", real_key)] = curr[("type", key_name[1])]
									way[("data", real_key)] = curr[("data", key_name[1])]
									break
								elif _mode[0] == "deep" and curr[("type", key_name[1])] == way[("type", real_key)]:
									if not isinstance(way[("data", real_key)], list):
										way[("data", real_key)] = lib0246.RevisionBatch(*way[("data", real_key)])
									if isinstance(curr[("data", key_name[1])], list):
										way[("data", real_key)].extend(curr[("data", key_name[1])])
									else:
										way[("data", real_key)].append(curr[("data", key_name[1])])
									break
								real_key += _pad[0]
				else:
					batch.append(curr)
					batch_count += 1

		return (way, junc, batch)

######################################################################################

class Beautify:
	@classmethod
	def INPUT_TYPES(s):
		return {
			"required": {
				"data": lib0246.ByPassTypeTuple(("*", )),
				"mode": (["basic", "more", "full", "json"], ),
			},
		}
	
	RETURN_TYPES = ()
	INPUT_IS_LIST = True
	OUTPUT_NODE = True
	FUNCTION = "execute"
	CATEGORY = "0246"

	def execute(self, data = None, mode = None, **kwargs):

		raw_mode = 0
		res_str = None
		match mode[0]:
			case "basic":
				raw_mode = 0
			case "more":
				raw_mode = 1
			case "full":
				raw_mode = 2
			case "json":
				res_str = None
				try:
					res_str = json.dumps(data, indent=2)
				except TypeError:
					res_str = "Cannot convert to JSON."
		
		if res_str is None:
			res_str = lib0246.beautify_structure(data, 0, raw_mode)

		return {
			"ui": {
				"text": [res_str]
			}
		}

######################################################################################

class Stringify:
	@classmethod
	def INPUT_TYPES(s):
		return {
			"required": {
				"_mode": (["basic", "value", "force"],),
				"_delimiter": ("STRING", {
					"default": ", ",
					"multiline": False
				}),
			},
		}
	
	RETURN_TYPES = ("STRING", )
	RETURN_NAMES = ("_str", )
	INPUT_IS_LIST = True
	FUNCTION = "execute"
	CATEGORY = "0246"

	def execute(self, _delimiter = None, _mode = None, **kwargs):
		res = []

		for value in kwargs.values():
			if isinstance(value, list):
				for item in value:
					if _mode[0] == "basic" and type(item).__str__ is object.__str__:
						continue
					elif _mode[0] == "value":
						if isinstance(item, object) and type(item).__module__ != 'builtins' and type(item).__str__ is object.__str__:
							continue
					try:
						item_str = str(item)
						if item_str:
							res.append(item_str)
					except Exception:
						continue

		res = _delimiter[0].join(res)
		return {
			"ui": {
				"text": [res]
			},
			"result": [res]
		}

######################################################################################

class BoxRange:
	@classmethod
	def INPUT_TYPES(s):
		return {
			"required": lib0246.WildDict({
				"script_method": (list(BoxRange.SUPPORT(0)), ),
				"script_order": ("STRING", {
					"default": "box",
					"multiline": False
				}),
			}),
			"hidden": {
				"_id": "UNIQUE_ID"
			}
		}
	
	@classmethod
	def SUPPORT(s, mode, method = None, box_range = None, box_ratio = None):
		# Designed to allow easy monkey patch for 3rd party
		match mode:
			case 0:
				return [
					"_",
					"(x, y)",
					"%(x, y)",
					"(width, height)",
					"%(width, height)",
					"(x, y, width, height)",
					"%(x, y, width, height)",
				]
			case 1:
				match method:
					case "%(x, y, width, height)":
						def temp_func(pin, res, **kwargs):
							if res is None:
								pin["x"] = []
								pin["y"] = []
								pin["width"] = []
								pin["height"] = []

								for i in range(len(box_range["data"])):
									pin["x"].append(lib0246.norm(
										box_range["data"][i][0],
										box_range["area"][0], box_range["area"][0] + box_range["area"][2]
									))
									pin["y"].append(lib0246.norm(
										box_range["data"][i][1],
										box_range["area"][1], box_range["area"][1] + box_range["area"][3]
									))
									pin["width"].append(box_range["data"][i][2] / box_range["area"][2])
									pin["height"].append(box_range["data"][i][3] / box_range["area"][3])
								return True
							return False
						return temp_func
					case _:
						raise Exception(f"\"{method}\" is not supported yet for BoxRange.")

	RETURN_TYPES = lib0246.ByPassTypeTuple(("*", ))
	RETURN_NAMES = lib0246.ByPassTypeTuple(("data", ))
	INPUT_IS_LIST = True
	OUTPUT_IS_LIST = (False, )
	FUNCTION = "execute"
	CATEGORY = "0246"

	def execute(self, _id = None, script_method = None, script_order = None, box_range = {}, box_ratio = {}):
		if isinstance(script_method, list):
			script_method = script_method[0]
		if isinstance(script_order, list):
			script_order = script_order[0]
		if isinstance(box_range, list):
			box_range = box_range[0]

		if script_method != "_":
			return (ScriptData({
				"id": _id,
				"func": BoxRange.SUPPORT(1, script_method, box_range, box_ratio),
				"order": script_order,
				"kind": "wrap"
			}), )
		return ({
			"box": box_range,
			"dim": box_ratio
		}, )
	
	@classmethod
	def IS_CHANGED(self, script_method = None, script_order = None, box_range = {}, box_ratio = {}, *args, **kwargs):
		if isinstance(box_range, list):
			box_range = box_range[0]
		return box_range

######################################################################################

class ScriptNode:
	@classmethod
	def INPUT_TYPES(s):
		return {
			"required": {
				"script_node": (list(nodes.NODE_CLASS_MAPPINGS.keys()), ),
				"script_pin_order": ("STRING", {
					"default": "",
					"multiline": False
				}),
				"script_pin_mode": (["pin_highway", "pin_junction", "pin_direct"], ),
				"script_res_order": ("STRING", {
					"default": "",
					"multiline": False
				}),
				"script_res_mode": (["res_junction", "res_highway_batch"], ),
			},
			"optional": {
				"pipe_in": lib0246.ByPassTypeTuple(("*", )),
			},
			"hidden": {
				"_prompt": "PROMPT",
				"_id": "UNIQUE_ID",
				"_workflow": "EXTRA_PNGINFO"
			}
		}
	
	RETURN_TYPES = (lib0246.TautologyStr("*"), "SCRIPT_DATA", "SCRIPT_DATA", "SCRIPT_DATA")
	RETURN_NAMES = ("pipe_out", "script_pin_data", "script_exec_data", "script_res_data")
	INPUT_IS_LIST = False
	OUTPUT_IS_LIST = lib0246.ContradictAll()
	FUNCTION = "execute"
	CATEGORY = "0246"

	def execute(
			self,
			_id = None, _prompt = None, _workflow = None,
			pipe_in = None,
			script_node = None,
			script_pin_order = None, script_pin_mode = None,
			script_res_order = None, script_res_mode = None,
			**kwargs
		):

		pin_func = None
		res_func = None
		pipe_flag = pipe_in is not None and isinstance(pipe_in, lib0246.RevisionDict)

		class_type = nodes.NODE_CLASS_MAPPINGS[script_node]

		input_type = getattr(class_type, "INPUT_TYPES")()
		if "required" not in input_type or len(input_type["required"]) == 0:
			raise Exception(f"Node class {_prompt[_id]['class_type']} does not have any required input.")
		
		output_type = getattr(class_type, "RETURN_TYPES")
		if len(output_type) == 0:
			raise Exception(f"Node class {_prompt[_id]['class_type']} does not have any output.")

		match script_pin_mode:
			case "pin_highway" if pipe_flag and pipe_in[("kind")] == "highway":
				def temp_func(pin, res, **kwargs):
					if res is None:
						iter_inst = pipe_in.path_iter(("data", ))
						for key in iter_inst:
							if isinstance(pipe_in[key], lib0246.RevisionBatch):
								if key[1] in pin:
									pin[key[1]].extend(pipe_in[key])
								else:
									pin[key[1]] = pipe_in[key]
							else:
								if key[1] in pin:
									pin[key[1]].append(pipe_in[key])
								else:
									pin[key[1]] = [pipe_in[key]]
						if "hidden" in input_type:
							for key in input_type["hidden"]:
								match input_type["hidden"][key]:
									case "PROMPT":
										pin[key] = [_prompt]
									case "UNIQUE_ID":
										pin[key] = [_id]
									case "EXTRA_PNGINFO":
										pin[key] = [_workflow]
						return True
					return False
				pin_func = temp_func
			case "pin_junction" if pipe_flag and pipe_in[("kind")] == "junction":
				def temp_func(pin, res, **kwargs):
					if res is None:
						junction_unpack(
							pipe_in, input_type,
							list(filter(lambda x: x != "hidden", input_type.keys())),
							base_dict=pin,
							pack_func=lambda _: [_],
							type_func=lambda _: "STRING" if isinstance(_, list) else _,
							fill_func=lambda d, k, v: d.setdefault(k, []).extend(v)
						)
						return True
					return False
				pin_func = temp_func
			case "pin_direct":
				raise Exception("pin_direct is not supported yet.")
			case _:
				pass

		match script_res_mode:
			case "res_junction":
				def temp_func(res, **kwargs):
					if res is not None:
						old_res = copy.copy(res)
						res.clear()
						res.append([lib0246.RevisionDict()])

						for curr_data in old_res:
							for type_name, curr_elem in zip(output_type, curr_data):
								junction_pack_loop(res[0][0], type_name, curr_elem)
						res[0][0][("kind")] = "junction"
						res[0][0][("id")] = _id

						return True
					return False
				res_func = temp_func
			case "res_highway_batch":
				def temp_func(res, **kwargs):
					if res is not None:
						old_res = copy.copy(res)
						res.clear()
						res.append([lib0246.RevisionDict()])

						name_list = getattr(class_type, "RETURN_NAMES") if hasattr(class_type, "RETURN_NAMES") else output_type
						for data_curr in old_res:
							for type_curr, name_curr, count in zip(output_type, name_list, range(len(output_type))):
								res[0][0][("type", name_curr)] = type_curr
								if ("data", name_curr) not in res[0][0]:
									res[0][0][("data", name_curr)] = lib0246.RevisionBatch()
								res[0][0][("data", name_curr)].append(data_curr[count])

						res[0][0][("kind")] = "highway"
						res[0][0][("id")] = _id
						return True
					return False
				res_func = temp_func
			case _:
				pass

		return (
			pipe_in,
			None if pin_func is None else ScriptData({
				"id": _id,
				"func": pin_func,
				"order": script_pin_order,
				"kind": "wrap"
			}), ScriptData({
				"id": _id,
				"node_name": script_node,
				"node_class": class_type,
				"node_inst": class_type(),
				"func": plan_exec_node,
				"kind": "exec"
			}),
			None if res_func is None else ScriptData({
				"id": _id,
				"func": res_func,
				"order": script_res_order,
				"kind": "wrap"
			})
		)

######################################################################################

class ScriptRule:
	@classmethod
	def INPUT_TYPES(s):
		return {
			"required": {
				"script_rule_mode": (["_", "slice", "cycle"], ),
			},
			"hidden": {
				"_id": "UNIQUE_ID",
			}
		}
	
	RETURN_TYPES = ("SCRIPT_DATA", )
	RETURN_NAMES = ("script_rule_data", )
	OUTPUT_IS_LIST = (False, False)
	FUNCTION = "execute"
	CATEGORY = "0246"

	def execute(
		self, _id = None, script_rule_mode = None
	):
		rule_data = None
		
		if script_rule_mode is not None:
			if script_rule_mode == "_":
				rule_data = ScriptData({
					"id": _id,
					"func": plan_rule_direct,
					"kind": "rule"
				})
			else:
				match script_rule_mode:
					case "slice":
						rule_data = ScriptData({
							"id": _id,
							"func": plan_rule_slice,
							"kind": "rule"
						})
					case "cycle":
						rule_data = ScriptData({
							"id": _id,
							"func": plan_rule_product,
							"kind": "rule"
						})
					case _:
						raise Exception(f"Invalid rule mode \"{script_rule_mode}\".")
					
		return (rule_data, )

######################################################################################

class Script:
	@classmethod
	def INPUT_TYPES(s):
		return {
			"required": {
				"_exec_mode": (["pass", "act"], ),
				"_sort_mode": ("STRING", {
					"default": "INT",
					"multiline": False
				}),
			},
			"optional": {
				"_script_in": ("SCRIPT_PIPE", ),
			},
			"hidden": {
				"_prompt": "PROMPT",
				"_id": "UNIQUE_ID",
				"_workflow": "EXTRA_PNGINFO"
			}
		}
	
	RETURN_TYPES = lib0246.ByPassTypeTuple(("SCRIPT_PIPE", ))
	RETURN_NAMES = lib0246.ByPassTypeTuple(("_script_out", ))
	INPUT_IS_LIST = True
	OUTPUT_IS_LIST = lib0246.TautologyRest()
	FUNCTION = "execute"
	CATEGORY = "0246"

	def execute(self, _id = None, _prompt = None, _workflow = None, _exec_mode = None, _sort_mode = None, _script_in = None, **kwargs):
		if isinstance(_prompt, list):
			_prompt = _prompt[0]
		if isinstance(_id, list):
			_id = _id[0]
		if isinstance(_workflow, list):
			_workflow = _workflow[0]

		if isinstance(_exec_mode, list):
			_exec_mode = _exec_mode[0]
		if isinstance(_sort_mode, list):
			_sort_mode = _sort_mode[0]

		if _script_in is None or len(_script_in) == 0:
			_script_in = lib0246.RevisionDict()
		else:
			_script_in = lib0246.RevisionDict(_script_in[0])

		script_wrap_count = _script_in.path_count(("script", "wrap"))

		for key in kwargs:
			for elem in kwargs[key]:
				if isinstance(elem, ScriptData):
					match elem["kind"]:
						case "exec" if "func" in elem:
							_script_in[("script", "exec")] = elem["func"]
							if "node_name" in elem:
								_script_in[("script", "node", "name")] = elem["node_name"]
								_script_in[("script", "node", "class")] = elem["node_class"]
								_script_in[("script", "node", "inst")] = elem["node_inst"]
						case "rule":
							_script_in[("script", "rule")] = elem["func"]
						case "wrap":
							_script_in[("script", "wrap", script_wrap_count)] = elem["func"]
							_script_in[("script", "order", script_wrap_count)] = elem["order"]
							_script_in[("script", "id", script_wrap_count)] = elem["id"]
							script_wrap_count += 1
				else:
					curr_nodes = _workflow["workflow"]["nodes"]
					node_index = next(i for i, _ in enumerate(curr_nodes) if _["id"] == int(_id))
					_script_in[("script", "data", next(_ for _ in curr_nodes[node_index]["inputs"] if _["name"] == key).get("label", key))] = elem

		pin = None
		res = []

		if _exec_mode == "act":
			# INT FLOAT UNSIGNED SIGNED REAL NOEXP NUMAFTER PATH COMPATIBILITYNORMALIZE
			# LOCALE LOCALEALPHA LOCALENUM IGNORECASE LOWERCASEFIRST GROUPLETTERS CAPITALFIRST
			# UNGROUPLETTERS NANLAST PRESORT

			_script_in.sort(
				("script", "order"), ("script", "wrap"),
				functools.reduce(
					lambda x, y: x | y,
					map(lambda _: getattr(natsort.ns, _.strip().upper()), _sort_mode.split(" "))
				)
			)

			inst = {
				"id": [_id],
				"prompt": _prompt,
				"workflow": _workflow,
			}

			pin = {}

			for key in _script_in.path_iter_arr(("script", "wrap")):
				if _script_in[key](script=_script_in, inst=inst, pin=pin, res=None):
					inst["id"].append(_script_in[("script", "id", key[2])])

			if ("script", "rule") in _script_in:
				_script_in[("script", "rule")](
					script=_script_in, inst=inst, pin=pin, res=res,
					func=functools.partial(
						_script_in.get(("script", "exec"), lambda *args, **kwargs: None),
						script=_script_in, inst=inst
					)
				)
			else:
				res.extend(_script_in[("script", "exec")](script=_script_in, inst=inst, pin=pin, res=res))

			inst["id"].clear()
			inst["id"].append(_id)

			for key in _script_in.path_iter_arr(("script", "wrap")):
				if _script_in[key](script=_script_in, inst=inst, pin=pin, res=res):
					inst["id"].append(_script_in[("script", "id", key[2])])

			res = lib0246.transpose(res, list)

		_script_in[("kind")] = "script"
		_script_in[("id")] = _id

		return {
			"ui": {
				"text": [""]
			},
			"result": [_script_in, *res]
		}

######################################################################################

class Hub:
	@classmethod
	def INPUT_TYPES(s):
		return {
			"required": lib0246.WildDict(),
			"hidden": {
				"_prompt": "PROMPT",
				"_id": "UNIQUE_ID",
				"_workflow": "EXTRA_PNGINFO"
			}
		}
	
	RETURN_TYPES = lib0246.TautologyDictStr()
	INPUT_IS_LIST = True
	OUTPUT_IS_LIST = lib0246.TautologyAll()
	FUNCTION = "execute"
	CATEGORY = "0246"

	SPECIAL = ["__PIPE__", "__BATCH_PRIM__", "__BATCH_COMBO__"]

	def execute(self, _id = None, _prompt = None, _workflow = None, **kwargs):
		# [TODO] Maybe set OUTPUT_IS_LIST depends on widget?
			# And allow dumping "node:..."?
		
		res_data = {}
		temp_data = {}
		type_data = {}
		name_data = {}

		curr_nodes = _workflow[0]["workflow"]["nodes"]
		self_index = next(i for i, _ in enumerate(curr_nodes) if _["id"] == int(_id[0]))
		curr_extra = _workflow[0]["workflow"]["extra"]

		for i, pin in enumerate(curr_nodes[self_index]["outputs"]):
			if pin["name"] in kwargs:
				if pin["name"].startswith("sole"):
					curr_type = curr_extra["0246.HUB_DATA"][_id[0]]["sole_type"][pin["name"]][-1]
					curr_index = next(i for i, _ in enumerate(curr_nodes[self_index]["outputs"]) if _["name"] == pin["name"])
					name_data[curr_index] = pin["name"]
					match curr_type:
						case "__BATCH_PRIM__" | "__BATCH_COMBO__" | "__PIPE__":
							temp_data[curr_index] = kwargs[pin["name"]][0]
						case _:
							res_data[curr_index] = kwargs[pin["name"]]
							type_data[curr_index] = curr_type
			else:
				res_data[i] = [None]

		for index_temp in temp_data:
			match curr_extra["0246.HUB_DATA"][_id[0]]["sole_type"][name_data[index_temp]][-1]:
				case "__BATCH_PRIM__":
					res_data[index_temp] = []
					for index_type in type_data:
						if type_data[index_type] == temp_data[index_temp]:
							res_data[index_temp].extend(res_data[index_type])
				case "__BATCH_COMBO__":
					res_data[index_temp] = []
					for index_type in type_data:
						if name_data[index_type].endswith(temp_data[index_temp] + ":COMBO"):
							res_data[index_temp].extend(res_data[index_type])
				case "__PIPE__":
					if temp_data[index_temp] == "HIGHWAY_PIPE":
						temp_res_data = lib0246.RevisionDict()
						for index_type in type_data:
							curr_list = curr_extra["0246.HUB_DATA"][_id[0]]["sole_type"][name_data[index_type]]
							name = curr_list[5] if len(curr_list) == 7 else index_type
							temp_res_data[("data", name)] = res_data[index_type]
							temp_res_data[("type", name)] = curr_list[-1]
						temp_res_data[("kind")] = "highway"
						temp_res_data[("id")] = _id[0]
						res_data[index_temp] = [temp_res_data]
					elif temp_data[index_temp] == "JUNCTION_PIPE":
						temp_res_data = lib0246.RevisionDict()
						for index_type in type_data:
							for value in res_data[index_type]:
								junction_pack_loop(
									temp_res_data,
									curr_extra["0246.HUB_DATA"][_id[0]]["sole_type"][name_data[index_type]][-1],
									value,
								)
						temp_res_data[("kind")] = "junction"
						temp_res_data[("id")] = _id[0]
						res_data[index_temp] = [temp_res_data]
					else:
						raise Exception(f"Invalid pipe type \"{temp_data[index_temp]}\".")
					
		if len(res_data) == 0:
			raise Exception("No output.")

		return {
			"ui": {
				"text": [""]
			},
			"result": [res_data[i] for i in range(len(res_data))]
		}

########################################################################################
######################################## EXPORT ########################################
########################################################################################

# [TODO] "Meta" node to show information about highway or junction
# [TODO] "BoxRangeMeta" node to output specific box and dim
# [TODO] "RandomInt" node can have linger seed if batch len is different

NODE_CLASS_MAPPINGS = {
	"0246.Highway": Highway,
	"0246.HighwayBatch": HighwayBatch,
	"0246.Junction": Junction,
	"0246.JunctionBatch": JunctionBatch,
	"0246.RandomInt": RandomInt,
	"0246.Count": Count,
	"0246.Hold": Hold,
	"0246.Loop": Loop,
	"0246.Beautify": Beautify,
	"0246.Stringify": Stringify,
	"0246.Merge": Merge,
	# "0246.Convert": Convert,
	"0246.BoxRange": BoxRange,
	"0246.ScriptNode": ScriptNode,
	"0246.ScriptRule": ScriptRule,
	"0246.Script": Script,
	"0246.Hub": Hub,
	# "0246.Pick": Pick,
}

NODE_DISPLAY_NAME_MAPPINGS = {
	"0246.Highway": "Highway",
	"0246.HighwayBatch": "Highway Batch",
	"0246.Junction": "Junction",
	"0246.JunctionBatch": "Junction Batch",
	"0246.RandomInt": "Random Int",
	"0246.Count": "Count",
	"0246.Hold": "Hold",
	"0246.Loop": "Loop",
	"0246.Beautify": "Beautify",
	"0246.Stringify": "Stringify",
	"0246.Merge": "Merge",
	# "0246.Convert": "Convert",
	"0246.BoxRange": "Box Range",
	"0246.ScriptNode": "Script Node",
	"0246.ScriptRule": "Script Rule",
	"0246.Script": "Script",
	"0246.Hub": "Hub",
	# "0246.Pick": "Pick",
}

print("\033[95m" + lib0246.HEAD_LOG + "Loaded all nodes and apis (/0246-parse)." + "\033[0m")