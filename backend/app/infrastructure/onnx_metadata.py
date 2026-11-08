"""Read ONNX protobuf metadata without loading tensors or importing a training runtime.

Field numbers follow the ONNX ModelProto/GraphProto/TensorProto schema. This
inspects structure and external references; it does not validate model operators.
"""
from pathlib import Path


def _varint(data, offset):
    value = 0
    for shift in range(0, 70, 7):
        if offset >= len(data):
            raise ValueError("Truncated protobuf varint")
        byte = data[offset]
        offset += 1
        value |= (byte & 127) << shift
        if not byte & 128:
            return value, offset
    raise ValueError("Invalid protobuf varint")


def _fields(data):
    offset = 0
    while offset < len(data):
        key, offset = _varint(data, offset)
        number, wire = key >> 3, key & 7
        if number == 0:
            raise ValueError("Invalid protobuf field")
        if wire == 0:
            value, offset = _varint(data, offset)
        elif wire in (1, 2, 5):
            if wire == 2:
                length, offset = _varint(data, offset)
            else:
                length = 8 if wire == 1 else 4
            if offset + length > len(data):
                raise ValueError("Truncated protobuf field")
            value = data[offset:offset + length]
            offset += length
        else:
            raise ValueError("Unsupported protobuf wire type")
        yield number, wire, value


def _messages(data, field):
    for number, wire, value in _fields(data):
        if number == field and wire == 2:
            yield value


def inspect_onnx(path):
    data = memoryview(Path(path).read_bytes())
    graph = next(_messages(data, 7), None)
    if graph is None:
        raise ValueError("Missing ONNX graph")
    locations = set()
    initializer_names = set()

    def tensor(value, initializer=False):
        for number, wire, content in _fields(value):
            if number == 8 and wire == 2 and initializer:
                initializer_names.add(bytes(content).decode("utf-8"))
            if number == 13 and wire == 2:
                entry = {n: bytes(v).decode("utf-8") for n, w, v in _fields(content) if w == 2}
                if entry.get(1) == "location":
                    locations.add(entry.get(2, ""))

    def sparse(value, initializer=False):
        for field in (1, 2):
            for content in _messages(value, field):
                tensor(content, initializer=initializer)

    def visit(value, depth=0):
        if depth > 64:
            raise ValueError("ONNX subgraph nesting exceeds limit")
        for field in _messages(value, 5):
            tensor(field, initializer=depth == 0)
        for field in _messages(value, 15):
            sparse(field, initializer=depth == 0)
        for node in _messages(value, 1):
            for attribute in _messages(node, 5):
                for number, wire, content in _fields(attribute):
                    if wire != 2:
                        continue
                    if number in (5, 10):
                        tensor(content)
                    elif number in (6, 11):
                        visit(content, depth + 1)
                    elif number in (22, 23):
                        sparse(content)
    visit(graph)
    inputs = []
    for value in _messages(graph, 11):
        name_bytes = next(_messages(value, 1), None)
        name = bytes(name_bytes).decode("utf-8") if name_bytes is not None else ""
        if name in initializer_names:
            continue
        dimensions = []
        for type_proto in _messages(value, 2):
            for tensor_type in _messages(type_proto, 1):
                for shape in _messages(tensor_type, 2):
                    for dimension in _messages(shape, 1):
                        item = None
                        for number, wire, content in _fields(dimension):
                            if number == 1 and wire == 0:
                                item = content if content < (1 << 63) else content - (1 << 64)
                            elif number == 2 and wire == 2:
                                item = bytes(content).decode("utf-8") or None
                        dimensions.append(item)
        inputs.append({"name": name, "dimensions": dimensions})
    # Retain the original numeric result for existing packaging checks.
    first_dimensions = [value if isinstance(value, int) and value > 0 else 0 for value in inputs[0]["dimensions"]] if inputs else []
    return {"external_files": sorted(locations), "input_dimensions": first_dimensions, "inputs": inputs}
