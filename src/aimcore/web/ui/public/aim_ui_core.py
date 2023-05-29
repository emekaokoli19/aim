####################
# Bindings for fetching Aim Objects
####################

from pyodide.ffi import create_proxy
from js import search, localStorage
import json
import hashlib


board_id = None


def deep_copy(obj):
    if isinstance(obj, (list, tuple)):
        return type(obj)(deep_copy(x) for x in obj)
    elif isinstance(obj, dict):
        return type(obj)((deep_copy(k), deep_copy(v)) for k, v in obj.items())
    elif isinstance(obj, set):
        return type(obj)(deep_copy(x) for x in obj)
    elif hasattr(obj, '__dict__'):
        result = type(obj)()
        result.__dict__.update(deep_copy(obj.__dict__))
        return result
    elif isinstance(obj, memoryview):
        return memoryview(bytes(obj))
    else:
        return obj


memoize_cache = {}


def memoize(func):
    def wrapper(*args, **kwargs):
        if func.__name__ not in memoize_cache:
            memoize_cache[func.__name__] = {}

        key = generate_key(args + tuple(kwargs.items()))

        if key not in memoize_cache[func.__name__]:
            memoize_cache[func.__name__][key] = func(*args, **kwargs)

        return memoize_cache[func.__name__][key]

    return wrapper


query_result_cache = {}


def query_filter(type_, query=""):
    query_key = f'{type_}_{query}'

    if query_key in query_result_cache:
        return query_result_cache[query_key]

    try:
        data = search(board_id, type_, query)
        data = create_proxy(data.to_py())
        items = []
        i = 0
        for item in data:
            d = item
            d["type"] = type_
            d["key"] = i
            i = i + 1
            items.append(d)
        data.destroy()

        query_result_cache[query_key] = items

        return items
    except:  # noqa
        return []


class Metric():
    @classmethod
    def filter(self, query=""):
        return query_filter('Metric', query)


class Images():
    @classmethod
    def filter(self, query=""):
        return query_filter('Images', query)


class Audios():
    @classmethod
    def filter(self, query=""):
        return query_filter('Audios', query)


class Texts():
    @classmethod
    def filter(self, query=""):
        return query_filter('Texts', query)


class Figures():
    @classmethod
    def filter(self, query=""):
        return query_filter('Figures', query)


class Distributions():
    @classmethod
    def filter(self, query=""):
        return query_filter('Distributions', query)


####################
# Bindings for visualizing data with data viz elements
####################


def find(obj, element):
    keys = element.split(".")
    rv = obj
    for key in keys:
        try:
            rv = rv[key]
        except:  # noqa
            return None
    return rv


colors = [
    "#3E72E7",
    "#18AB6D",
    "#7A4CE0",
    "#E149A0",
    "#E43D3D",
    "#E8853D",
    "#0394B4",
    "#729B1B",
]

stroke_styles = [
    "none",
    "5 5",
    "10 5 5 5",
    "10 5 5 5 5 5",
    "10 5 5 5 5 5 5 5",
    "20 5 10 5",
    "20 5 10 5 10 5",
    "20 5 10 5 10 5 5 5",
    "20 5 10 5 5 5 5 5",
]


def generate_key(data):
    content = str(data)
    return hashlib.md5(content.encode()).hexdigest()


viz_map_keys = {}


def update_viz_map(viz_type, key=None):
    if key is not None:
        viz_map_keys[key] = key
        return key
    if viz_type in viz_map_keys:
        viz_map_keys[viz_type] = viz_map_keys[viz_type] + 1
    else:
        viz_map_keys[viz_type] = 0

    viz_key = viz_type + str(viz_map_keys[viz_type])

    return viz_key


def apply_group_value_pattern(value, list):
    if type(value) is int:
        return list[value % len(list)]
    return value


@memoize
def group(name, data, options, key=None):
    group_map = {}
    grouped_data = []
    items = deep_copy(data)
    for item in items:
        group_values = []
        if callable(options):
            val = options(item)
            if type(val) == bool:
                val = int(val)
            group_values.append(val)
        else:
            for opt in options:
                val = find(
                    item,
                    str(opt) if type(opt) is not str else opt.replace(
                        "metric.", ""),
                )
                group_values.append(val)

        group_key = generate_key(group_values)

        if group_key not in group_map:
            group_map[group_key] = {
                "options": options,
                "val": group_values,
                "order": None,
            }
        item[name] = group_key
        grouped_data.append(item)
    sorted_groups = group_map
    if callable(options):
        sorted_groups = {
            k: v
            for k, v in sorted(
                sorted_groups.items(), key=lambda x: str(x[1]["val"]), reverse=True
            )
        }
    else:
        for i, opt in enumerate(options):
            sorted_groups = {
                k: v
                for k, v in sorted(
                    sorted_groups.items(),
                    key=lambda x: (3, str(x[1]["val"][i]))
                    if type(x[1]["val"][i]) in [tuple, list, dict]
                    else (
                        (0, int(x[1]["val"][i]))
                        if str(x[1]["val"][i]).isdigit()
                        else (
                            (2, str(x[1]["val"][i]))
                            if x[1]["val"][i] is None
                            else (1, str(x[1]["val"][i]))
                        )
                    ),
                )
            }

    i = 0
    for group_key in sorted_groups:
        sorted_groups[group_key]["order"] = (
            sorted_groups[group_key]["val"][0] if callable(options) else i
        )
        i = i + 1
    return sorted_groups, grouped_data


current_layout = []


saved_state_str = localStorage.getItem("app_state")

state = {}

if saved_state_str:
    state = json.loads(saved_state_str)


def set_state(update, board_id, persist=False):
    from js import setState

    if board_id not in state:
        state[board_id] = {}

    state[board_id].update(update)

    setState(state, board_id, persist)


block_context = {
    "current": 0,
}


def render_to_layout(data):
    from js import updateLayout

    is_found = False
    for i, cell in enumerate(current_layout):
        if cell["key"] == data["key"]:
            current_layout[i] = data
            is_found = True

    if is_found == False:
        current_layout.append(data)

    updateLayout(current_layout, data["board_id"])


class Element:
    def __init__(self, block=None):
        self.parent_block = block
        self.board_id = board_id


class Block(Element):
    def __init__(self, type_, data=None, block=None):
        super().__init__(block)
        block_context["current"] += 1
        self.block_context = {
            "id": block_context["current"],
            "type": type_
        }
        self.key = generate_key(self.block_context)

        self.data = data
        self.callbacks = {}
        self.options = {}

        self.render()

    def render(self):
        block_data = {
            "element": 'block',
            "block_context": self.block_context,
            "key": self.key,
            "parent_block": self.parent_block,
            "board_id": self.board_id,
            "data": self.data,
            "options": self.options,
            "callbacks": self.callbacks,
        }

        render_to_layout(block_data)

    def __enter__(self):
        ui.set_block_context(self.block_context)

    def __exit__(self, type, value, traceback):
        ui.set_block_context(None)


class Component(Element):
    def __init__(self, key, type_, block):
        super().__init__(block)
        self.state = {}
        self.key = key
        self.type = type_
        self.data = None
        self.callbacks = {}
        self.options = {}
        self.state = state[board_id][key] if board_id in state and key in state[board_id] else {
        }
        self.no_facet = True

    def set_state(self, value):
        should_batch = self.parent_block is not None and self.parent_block["type"] == "form"

        if should_batch:
            state_slice = state[self.board_id][
                self.parent_block["id"]
            ] if (self.board_id in state and self.parent_block["id"] in state[self.board_id]) else {}

            component_state_slice = state_slice[self.key] if self.key in state_slice else {
            }

            component_state_slice.update(value)

            state_slice.update({
                self.key: component_state_slice
            })

            set_state({
                self.parent_block["id"]: state_slice
            }, self.board_id)
        else:
            state_slice = state[self.board_id][
                self.key
            ] if (self.board_id in state and self.key in state[self.board_id]) else {}

            state_slice.update(value)

            set_state({
                self.key: state_slice
            }, self.board_id)

    def render(self):
        component_data = {
            "type": self.type,
            "key": self.key,
            "data": self.data,
            "callbacks": self.callbacks,
            "options": self.options,
            "parent_block": self.parent_block,
            "no_facet": self.no_facet,
            "board_id": self.board_id
        }

        component_data.update(self.state)

        render_to_layout(component_data)


class AimSequenceComponent(Component):
    def group(self, prop, value=[]):
        group_map, group_data = group(prop, self.data, value, self.key)

        items = []
        for i, item in enumerate(self.data):
            elem = dict(item)
            current = group_map[group_data[i][prop]]

            if prop == "color":
                color_val = apply_group_value_pattern(
                    current["order"], colors
                )
                elem["color"] = color_val
                elem["color_val"] = current["val"]
                elem["color_options"] = value
            elif prop == "stroke_style":
                stroke_val = apply_group_value_pattern(
                    current["order"], stroke_styles
                )
                elem["dasharray"] = stroke_val
                elem["dasharray_val"] = current["val"]
                elem["dasharray_options"] = value
            else:
                elem[prop] = current["order"]
                elem[f"{prop}_val"] = current["val"]
                elem[f"{prop}_options"] = value

            if prop == "row" or prop == "column":
                self.no_facet = False

            items.append(elem)

        self.data = items

        self.render()


# AimSequenceVizComponents


class LineChart(AimSequenceComponent):
    def __init__(self, data, x, y, color=[], stroke_style=[], options={}, key=None, block=None):
        component_type = "LineChart"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        color_map, color_data = group("color", data, color, component_key)
        stroke_map, stroke_data = group(
            "stroke_style", data, stroke_style, component_key)
        lines = []
        for i, item in enumerate(data):
            color_val = apply_group_value_pattern(
                color_map[color_data[i]["color"]]["order"], colors
            )
            stroke_val = apply_group_value_pattern(
                stroke_map[stroke_data[i]["stroke_style"]
                           ]["order"], stroke_styles
            )

            line = dict(item)
            line["key"] = i
            line["data"] = {"xValues": find(item, x), "yValues": find(item, y)}
            line["color"] = color_val
            line["dasharray"] = stroke_val

            lines.append(line)

        self.data = lines
        self.options = options
        self.callbacks = {
            "on_active_point_change": self.on_active_point_change
        }

        self.render()

    @property
    def active_line(self):
        return self.state["active_line"] if "active_line" in self.state else None

    @property
    def focused_line(self):
        return self.state["focused_line"] if "focused_line" in self.state else None

    @property
    def active_point(self):
        return self.state["active_point"] if "active_point" in self.state else None

    @property
    def focused_point(self):
        return self.state["focused_point"] if "focused_point" in self.state else None

    async def on_active_point_change(self, point, is_active):
        if point is not None:
            item = self.data[point.key]

            if is_active:
                self.set_state({
                    "focused_line": item,
                    "focused_point": point,
                })
            else:
                self.set_state({
                    "active_line": item,
                    "active_point": point,
                })


class ImagesList(AimSequenceComponent):
    def __init__(self, data, key=None, block=None):
        component_type = "Images"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        images = []

        for i, item in enumerate(data):
            image = item
            image["key"] = i

            images.append(image)

        self.data = images

        self.render()


class AudiosList(AimSequenceComponent):
    def __init__(self, data, key=None, block=None):
        component_type = "Audios"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        audios = []

        for i, item in enumerate(data):
            audio = item
            audio["key"] = i

            audios.append(audio)

        self.data = audios

        self.render()


class TextsList(AimSequenceComponent):
    def __init__(self, data, color=[], key=None, block=None):
        component_type = "Texts"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        color_map, color_data = group("color", data, color, component_key)

        texts = []

        for i, item in enumerate(data):
            color_val = apply_group_value_pattern(
                color_map[color_data[i]["color"]]["order"], colors
            )
            text = item
            text["key"] = i
            text["color"] = color_val

            texts.append(text)

        self.data = texts

        self.render()


class FiguresList(AimSequenceComponent):
    def __init__(self, data, key=None, block=None):
        component_type = "Figures"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        figures = []

        for i, item in enumerate(data):
            figure = {
                "key": i,
                "data": item.to_json(),
            }

            figures.append(figure)

        self.data = figures

        self.render()


class Union(Component):
    def __init__(self, components, key=None, block=None):
        component_type = "Union"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        for i, elem in reversed(list(enumerate(current_layout))):
            for comp in components:
                if elem["key"] == comp.key:
                    del current_layout[i]

        self.data = []
        for comp in components:
            self.data = self.data + comp.data
            self.callbacks.update(comp.callbacks)

        def get_viz_for_type(type):
            for comp in components:
                if comp.data and comp.data[0] and comp.data[0]["type"] == type:
                    return comp.type

        self.type = get_viz_for_type

        self.render()


# DataDisplayComponents


class Plotly(Component):
    def __init__(self, fig, key=None, block=None):
        component_type = "Plotly"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.data = fig.to_json()

        self.render()


class JSON(Component):
    def __init__(self, data, key=None, block=None):
        component_type = "JSON"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.data = data

        self.render()


class DataFrame(Component):
    def __init__(self, data, key=None, block=None):
        component_type = "DataFrame"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.data = data.to_json(orient="records")

        self.render()


class Table(Component):
    def __init__(self, data, key=None, block=None):
        component_type = "Table"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.data = data

        self.callbacks = {
            "on_row_select": self.on_row_select,
            'on_row_focus': self.on_row_focus
        }
        self.options = {
            "data": data
        }

        self.render()

    @property
    def selected_rows(self):
        return self.state["selected_rows"] if "selected_rows" in self.state else None

    @property
    def focused_row(self):
        return self.state["focused_row"] if "focused_row" in self.state else None

    async def on_row_select(self, val):
        self.set_state({"selected_rows": val.to_py()})

    async def on_row_focus(self, val):
        self.set_state({"focused_row": val.to_py()})


class HTML(Component):
    def __init__(self, data, key=None, block=None):
        component_type = "HTML"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.data = data

        self.render()


class Text(Component):
    def __init__(self, data, component=None, size=None, weight=None, color=None, mono=None, key=None, block=None):
        component_type = "Text"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.data = data

        self.options = {
            "component": component,
            "size": size,
            "weight": weight,
            "color": color,
            "mono": mono
        }

        self.render()


class Link(Component):
    def __init__(self, text, to, new_tab=False, key=None, block=None):
        component_type = "Link"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.data = to

        self.options = {
            "text": text,
            "to": to,
            "new_tab": new_tab
        }

        self.render()


# AimHighLevelComponents


class RunMessages(Component):
    def __init__(self, run_hash, key=None, block=None):
        component_type = "RunMessages"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.data = run_hash

        self.render()


class RunLogs(Component):
    def __init__(self, run_hash, key=None, block=None):
        component_type = "RunLogs"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.data = run_hash

        self.render()


class RunNotes(Component):
    def __init__(self, run_hash, key=None, block=None):
        component_type = "RunNotes"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.data = run_hash

        self.render()


# InputComponents


def get_component_batch_state(key, parent_block=None):
    if parent_block is None:
        return None

    if board_id in state and parent_block["id"] in state[board_id]:
        if key in state[board_id][parent_block["id"]]:
            return state[board_id][parent_block["id"]][key]

    return None

# Type checker helper functions

def is_num(value):
    return isinstance(value, int) or isinstance(value, float)

def is_str(value):
    return isinstance(value, str)

def is_bool(value):
    return isinstance(value, bool)

def is_list(value):
    return isinstance(value, list)

def is_dict(value):
    return isinstance(value, dict)

def is_tuple(value):
    return isinstance(value, tuple)

# check if value is a number, otherwise raise an exception
def safe_num(value):
    if (is_num(value)):
        return value
    else:
        raise Exception("Value must be a number")

 # check if value is a string, otherwise raise an exception
def safe_str(value):
    if (is_str(value)):
        return value
    else:
        raise Exception("Value must be a string")

 # check if value is a boolean, otherwise raise an exception
def safe_bool(value):
     if (is_bool(value)):
          return value
     else:
          raise Exception("Value must be a boolean")

 # check if value is a list, otherwise raise an exception
def safe_list(value):
    if (is_list(value)):
        return value
    else:
        raise Exception("Value must be a list")

 # check if value is a dict, otherwise raise an exception
def safe_dict(value):
    if (is_dict(value)):
        return value
    else:
        raise Exception("Value must be a dict")

 # check if value is a tuple, otherwise raise an exception
def safe_tuple(value):
    if (is_tuple(value)):
        return value
    else:
        raise Exception("Value must be a tuple")

 # check if all elements in list are numbers, otherwise raise an exception
def safe_num_list(value):
    if(all([is_num(item) for item in value]))
        return value
    else:
        raise Exception("Value must be a list of numbers")

 # check if all elements in tuple are numbers, otherwise raise an exception
def safe_num_tuple(value):
    if(all([is_num(item) for item in value]))
        return value
    else:
        raise Exception("Value must be a tuple of numbers")


class Slider(Component):
    def __init__(self, label='', value=10, min=0, max=100, step=None, disabled=False, key=None, block=None):
        component_type = "Slider"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.data = safe_num(value)

        batch_state = get_component_batch_state(component_key, block)

        self.options = {
            "value": self.value if batch_state is None else batch_state["value"][0],
            "label": safe_str(label),
            "min": safe_num(min),
            "max": safe_num(max),
            "step": self._get_step(self.data, step),
            "disabled": safe_bool(disabled),
        }

        self.callbacks = {
            "on_change": self.on_change
        }

        self.render()

    def _get_step(self, initial_value, step):
        if (step):
            return safe_num(step)
        elif isinstance(initial_value, float):
            return 0.01
        else:
            return 1

    @property
    def value(self):
        return self.state["value"][0] if "value" in self.state else self.data

    async def on_change(self, val):
        self.set_state({"value": val.to_py()})


class RangeSlider(Component):
    def __init__(self, label='', value=(0, 10), min=0, max=100, step=None, disabled=False, key=None, block=None):
        component_type = "RangeSlider"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.data = sorted(safe_num_tuple(value), key=int)

        batch_state = get_component_batch_state(component_key, block)

        self.options = {
            "value": self.value if batch_state is None else batch_state["value"],
            "label": safe_str(label),
            "min": safe_num(min),
            "max": safe_num(max),
            "step": self._get_step(self.data, step),
            "disabled": safe_bool(disabled),
        }

        self.callbacks = {
            "on_change": self.on_change
        }

        self.render()

    def _get_step(self, initial_range, step):
        if (step):
            return safe_num(step)
        elif any(isinstance(n, float) for n in initial_range):
            return 0.01
        else:
            return 1

    @property
    def value(self):
        value_state = self.state["value"] if "value" in self.state else self.data
        return tuple(value_state)

    async def on_change(self, val):
        self.set_state({"value": tuple(val.to_py())})


class TextInput(Component):
    def __init__(self, label='', value='', disabled=False, key=None, block=None):
        component_type = "TextInput"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.data = safe_str(value)

        batch_state = get_component_batch_state(component_key, block)

        self.options = {
            "value": self.value if batch_state is None else batch_state["value"],
            "label": safe_str(label),
            "disabled": safe_bool(disabled),
        }

        self.callbacks = {
            "on_change": self.on_change
        }

        self.render()

    @property
    def value(self):
        return self.state["value"] if "value" in self.state else self.data

    async def on_change(self, val):
        self.set_state({"value": val})


class NumberInput(Component):
    def __init__(self, label='', value=0, min=None, max=None, step=None, disabled=False, key=None, block=None):
        component_type = "NumberInput"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.data = safe_num(value)

        batch_state = get_component_batch_state(component_key, block)

        self.options = {
            "value": self.value if batch_state is None else batch_state["value"],
            "label": safe_str(label),
            "min": min if is_num(min) else None,
            "max": max if is_num(min) else None,
            "step": self._get_step(self.value, step),
            "disabled": safe_bool(disabled),
        }

        self.callbacks = {
            "on_change": self.on_change
        }

        self.render()

    def _get_step(self, value, step):
        if (step):
            return safe_num(step)
        elif isinstance(value, float):
            return 0.01
        else:
            return 1

    @property
    def value(self):
        return self.state["value"] if "value" in self.state else self.data

    async def on_change(self, val):
        self.set_state({"value": val})


class Select(Component):
    def __init__(self, options=(), value=None, key=None, block=None):
        component_type = "Select"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.default = value

        batch_state = get_component_batch_state(component_key, block)

        self.options = {
            "isMulti": False,
            "value": self.value if batch_state is None else batch_state["value"],
            "options": options
        }

        self.callbacks = {
            "on_change": self.on_change
        }

        self.render()

    @property
    def value(self):
        return self.state["value"] if "value" in self.state else self.default

    async def on_change(self, val, index):
        self.set_state({"value": val})


class MultiSelect(Component):
    def __init__(self, options=(), value=None, key=None, block=None):
        component_type = "Select"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.default = value

        batch_state = get_component_batch_state(component_key, block)

        self.options = {
            "isMulti": True,
            "value": self.value if batch_state is None else batch_state["value"],
            "options": options
        }

        self.callbacks = {
            "on_change": self.on_change
        }

        self.render()

    @property
    def value(self):
        return self.state["value"] if "value" in self.state else self.default

    async def on_change(self, val, index):
        if type(self.value) is list:
            if val in self.value:
                value = list(filter(lambda item: item != val, self.value))
            else:
                value = self.value + [val]

            self.set_state({"value": value})


class Switch(Component):
    def __init__(self, checked=None, size=None, defaultChecked=None, disabled=None, key=None, block=None):
        component_type = "Switch"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.data = checked

        self.options = {
            "size": size,
            "defaultChecked": defaultChecked,
            "disabled": disabled,
        }

        self.callbacks = {
            "on_change": self.on_change
        }

        self.render()

    @property
    def value(self):
        return self.state["value"] if "value" in self.state else self.data

    async def on_change(self, val):
        self.set_state({"value": val})


class TextArea(Component):
    def __init__(self, value=None, size=None, resize=None, disabled=None, caption=None, key=None, block=None):
        component_type = "TextArea"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.data = value

        batch_state = get_component_batch_state(component_key, block)

        self.options = {
            "value": self.value if batch_state is None else batch_state["value"],
            "size": size,
            "resize": resize,
            "disabled": disabled,
            "caption": caption
        }

        self.callbacks = {
            "on_change": self.on_change
        }

        self.render()

    @property
    def value(self):
        return self.state["value"] if "value" in self.state else self.data

    async def on_change(self, val):
        self.set_state({"value": val})


class Radio(Component):
    def __init__(self, label=None, options=(), index=0, orientation='vertical', disabled=None, key=None, block=None):
        component_type = "Radio"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.default = options[index]

        self.options = {
            "value": self.value,
            "label": label,
            "options": options,
            "orientation": orientation,
            "disabled": disabled,
        }

        self.callbacks = {
            "on_change": self.on_change
        }

        self.render()

    @property
    def value(self):
        return self.state["value"] if "value" in self.state else self.default

    async def on_change(self, val):
        self.set_state({"value": val})


class Checkbox(Component):
    def __init__(self, checked=False, disabled=None, key=None, block=None):
        component_type = "Checkbox"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.data = checked

        self.options = {
            "disabled": disabled,
        }

        self.callbacks = {
            "on_change": self.on_change
        }

        self.render()

    @property
    def value(self):
        return self.state["value"] if "value" in self.state else self.data

    async def on_change(self, val):
        self.set_state({"value": val})


class ToggleButton(Component):
    def __init__(self, left_value="On", right_value="Off", index=0, disabled=None, size=None, block=None, key=None):
        component_type = "ToggleButton"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.options = {
            "rightLabel": right_value,
            "leftLabel": left_value,
            "rightValue": right_value,
            "leftValue": left_value,
            "disabled": disabled,
            "size": size,
            "defaultValue": left_value if index == 0 else right_value,
        }

        self.callbacks = {
            "on_change": self.on_change
        }

        self.render()

    @property
    def value(self):
        return self.state["value"] if "value" in self.state else self.options["defaultValue"]

    async def on_change(self, val):
        self.set_state({"value": val})


class TypographyComponent(Component):
    def __init__(self, text, component_type, options=None, key=None, block=None):
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.data = text
        self.options = options

        self.render()


class Header(TypographyComponent):
    def __init__(self, text, key=None, block=None):
        options = {
            "component": "h2",
            "size": "$9"
        }
        super().__init__(text, "Header", options, key, block)


class SubHeader(TypographyComponent):
    def __init__(self, text, key=None, block=None):
        options = {
            "component": "h3",
            "size": "$6"
        }
        super().__init__(text, "SubHeader", options, key, block)


# Super components

class Board(Component):
    def __init__(self, id=None, state=None, block=None, key=None):
        component_type = "Board"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.data = id

        set_state(state or {}, id)

        self.render()

    def get_state(self):
        return state[self.data] if self.data in state else None


class BoardLink(Component):
    def __init__(self, id=None, text='Go To Board', new_tab=False, state=None, block=None, key=None):
        component_type = "BoardLink"
        component_key = update_viz_map(component_type, key)
        super().__init__(component_key, component_type, block)

        self.data = id

        self.options = {
            "text": text,
            "new_tab": new_tab
        }

        set_state(state or {}, id)

        self.render()


class UI:
    def __init__(self):
        self.block_context = None

    def set_block_context(self, block):
        self.block_context = block

    # layout elements
    def rows(self, count):
        rows = []
        for i in range(count):
            row = Row(block=self.block_context)
            rows.append(row)
        return rows

    def columns(self, count):
        cols = []
        for i in range(count):
            col = Column(block=self.block_context)
            cols.append(col)
        return cols

    def tabs(self, names):
        tabs = Tabs(names, block=self.block_context)
        return tabs.tabs

    def form(self, *args, **kwargs):
        form = Form(*args, **kwargs, block=self.block_context)
        return form

    # input elements
    def text_input(self, *args, **kwargs):
        input = TextInput(*args, **kwargs, block=self.block_context)
        return input.value

    def number_input(self, *args, **kwargs):
        input = NumberInput(*args, **kwargs, block=self.block_context)
        return input.value

    def text_area(self, *args, **kwargs):
        textarea = TextArea(*args, **kwargs, block=self.block_context)
        return textarea.value

    def switch(self, *args, **kwargs):
        switch = Switch(*args, **kwargs, block=self.block_context)
        return switch.value

    def select(self, *args, **kwargs):
        select = Select(*args, **kwargs, block=self.block_context)
        return select.value

    def multi_select(self, *args, **kwargs):
        multi_select = MultiSelect(*args, **kwargs, block=self.block_context)
        return multi_select.value

    def slider(self, *args, **kwargs):
        slider = Slider(*args, **kwargs, block=self.block_context)
        return slider.value

    def range_slider(self, *args, **kwargs):
        range_slider = RangeSlider(*args, **kwargs, block=self.block_context)
        return range_slider.value

    def radio(self, *args, **kwargs):
        radio = Radio(*args, **kwargs, block=self.block_context)
        return radio.value

    def checkbox(self, *args, **kwargs):
        checkbox = Checkbox(*args, **kwargs, block=self.block_context)
        return checkbox.value

    def toggle_button(self, *args, **kwargs):
        toggle = ToggleButton(*args, **kwargs, block=self.block_context)
        return toggle.value

    # data display elements
    def text(self, *args, **kwargs):
        text = Text(*args, **kwargs, block=self.block_context)
        return text

    def plotly(self, *args, **kwargs):
        plotly_chart = Plotly(*args, **kwargs, block=self.block_context)
        return plotly_chart

    def json(self, *args, **kwargs):
        json = JSON(*args, **kwargs, block=self.block_context)
        return json

    def dataframe(self, *args, **kwargs):
        dataframe = DataFrame(*args, **kwargs, block=self.block_context)
        return dataframe

    def table(self, *args, **kwargs):
        table = Table(*args, **kwargs, block=self.block_context)
        return table

    def html(self, *args, **kwargs):
        html = HTML(*args, **kwargs, block=self.block_context)
        return html

    def link(self, *args, **kwargs):
        link = Link(*args, **kwargs, block=self.block_context)
        return link

    def header(self, *args, **kwargs):
        header = Header(*args, **kwargs, block=self.block_context)
        return header

    def subheader(self, *args, **kwargs):
        subheader = SubHeader(*args, **kwargs, block=self.block_context)
        return subheader

    # Aim sequence viz components
    def line_chart(self, *args, **kwargs):
        line_chart = LineChart(*args, **kwargs, block=self.block_context)
        return line_chart

    def images(self, *args, **kwargs):
        images = ImagesList(*args, **kwargs, block=self.block_context)
        return images

    def audios(self, *args, **kwargs):
        audios = AudiosList(*args, **kwargs, block=self.block_context)
        return audios

    def figures(self, *args, **kwargs):
        figures = FiguresList(*args, **kwargs, block=self.block_context)
        return figures

    def texts(self, *args, **kwargs):
        texts = TextsList(*args, **kwargs, block=self.block_context)
        return texts

    def union(self, *args, **kwargs):
        union = Union(*args, **kwargs, block=self.block_context)
        return union

    # Aim high level components
    def run_messages(self, *args, **kwargs):
        run_messages = RunMessages(*args, **kwargs, block=self.block_context)
        return run_messages

    def run_logs(self, *args, **kwargs):
        run_logs = RunLogs(*args, **kwargs, block=self.block_context)
        return run_logs

    def run_notes(self, *args, **kwargs):
        run_notes = RunNotes(*args, **kwargs, block=self.block_context)
        return run_notes

    # Super components
    def board(self, *args, **kwargs):
        board = Board(*args, **kwargs, block=self.block_context)
        return board

    def board_link(self, *args, **kwargs):
        board = BoardLink(*args, **kwargs, block=self.block_context)
        return board


class Row(Block, UI):
    def __init__(self, block=None):
        super().__init__('row', block=block)


class Column(Block, UI):
    def __init__(self, block=None):
        super().__init__('column', block=block)


class Tab(Block, UI):
    def __init__(self, label, block=None):
        super().__init__('tab', data=label, block=block)

        self.data = label


class Tabs(Block, UI):
    def __init__(self, labels, block=None):
        super().__init__('tabs', block=block)

        self.tabs = []
        for label in labels:
            tab = Tab(label, block=self.block_context)
            self.tabs.append(tab)


class Form(Block, UI):
    def __init__(self, submit_button_label='Submit', block=None):
        super().__init__('form', block=block)

        self.options = {
            'submit_button_label': submit_button_label
        }
        self.callbacks = {
            'on_submit': self.submit
        }

        self.render()

    def submit(self):
        batch_id = self.block_context["id"]
        state_update = state[board_id][batch_id]
        set_state(state_update, board_id=self.board_id)


ui = UI()
