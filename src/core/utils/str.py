import ast


def str_to_obj(string):
    try:
        s = ast.literal_eval(str(string))
        if type(s) == tuple:  # noqa
            return s
        if type(s) == list:  # noqa
            return s
        return s
    except:  # noqa
        return string
