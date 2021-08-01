

def raisesAssertionError(method, *args, **kwargs):
    try:
        method(*args, **kwargs)
    except AssertionError as error:
        return error
    else:
        raise AssertionError(f"Assertionerror not raised on {method_name}")
