error_exceptions = ["Timestamp for this request was 1000ms ahead of the server's time",
                    "Timestamp for this request is outside of the recvWindow",
                    "invalid request, please check your timestamp and recv_window param"]


def is_exception(error: str):
    return any(er.lower() in str(error).lower()
               for er in error_exceptions)


def round_to_one(number: float):
    negative_positive = 1
    if number < 0:
        number = abs(number)
        negative_positive = -1

    if round(number, 1) != 0:
        number = round(number, 1)
    else:
        # rounds 0.00062352356 to 0.0006
        count = 0
        for n in str(number).replace('.', ''):
            count += 1
            if n != '0':
                number = round(number, count - 1)
                break
    number *= negative_positive
    return number


def round_all_floats(_dict, exceptions=()):
    for k, v in _dict.items():
        if isinstance(v, float) and k not in exceptions:
            _dict[k] = round_to_one(v)
    return _dict


data = [
    {
        'type': 'line',
        'color': 'green',
        'name': 'мой USD кошелек',
        'value': [1, 5, 8],
        'time': [1, 4, 5],
        'info': ['J2Ph3qLLxI', 'lIy6DhO3jD', '5UbeITXcFK']
    },
    {
        'type': 'points',
        'color': 'red',
        'name': 'DOTS',
        'value': [2, 3, 7],
        'time': [1, 4, 5],
        'info': ['J2Ph3qLLxI', 'lIy6DhO3jD', '5UbeITXcFK']
    }
]


def bokeh_chart(data: list) -> None:
    fig = figure(
        height=800, width=1000,
        x_axis_label='Date', y_axis_label='$',
        toolbar_location="above", y_axis_location="right",
        x_axis_type='datetime',
        tools=['pan', 'crosshair', 'wheel_zoom', 'box_zoom', 'reset', 'save'],
        tooltips=[("time", "@x"), ("value", "@y"), ("info", "@info")]
    )

    for d in data:
        d['source'] = ColumnDataSource(
            data=dict(x=d['time'], y=d['value'], info=d['info']))
        if d['type'] == 'line':
            fig.line('x', 'y', legend_label=d['name'], line_color=d['color'],
                     line_width=2, source=d['source'])
        elif d['type'] == 'points':
            fig.circle("x", "y", legend_label=d['name'], color=d['color'],
                       size=10, source=d['source'])

    fig.legend.location = "top_left"

    x = ['1', '2', '3']
    y = [1, 2, 4]
    fig1 = figure(x_range=x, height=800, width=1000,
                  y_axis_location="right", x_axis_type='datetime')
    fig1.vbar(x=x, top=y, width=0.1, alpha=0.2)
    g = gridplot([[fig1, fig]], merge_tools=True)
    g.toolbar.logo = None

    show(g)


NEW_ERRORS_DAY = None
NEW_ERRORS_HOUR = None


def get_new_errors():
    initial_data_day = get_errors_tv(timeframe='day', last_errors=False)
    initial_data_hour = get_errors_tv(timeframe='hour', last_errors=False)

    global NEW_ERRORS_DAY, NEW_ERRORS_HOUR
    while True:
        new_data_day = get_errors_tv(timeframe='day')
        new_data_hour = get_errors_tv(timeframe='hour')
        NEW_ERRORS_DAY = [error for error in new_data_day
                          if error not in initial_data_day]
        NEW_ERRORS_HOUR = [error for error in new_data_hour
                           if error not in initial_data_hour]
        if NEW_ERRORS_DAY:
            initial_data_day = new_data_day
            initial_data_hour = new_data_hour
        time.sleep(3)


async def connect_client(_client: websockets.WebSocketServerProtocol):
    if not _client.path.startswith('/websocket/'):
        return None

    initial_new_errors_day = None
    while True:
        if NEW_ERRORS_DAY and initial_new_errors_day != NEW_ERRORS_DAY:
            try:
                timeframe = _client.path.split("/websocket/")[1]
                if timeframe == 'day':
                    await _client.send(json.dumps(NEW_ERRORS_DAY))
                elif timeframe == 'hour':
                    await _client.send(json.dumps(NEW_ERRORS_HOUR))
            except ConnectionClosedOK:
                break
            initial_new_errors_day = NEW_ERRORS_DAY
        await asyncio.sleep(3)


Thread(target=get_new_errors).start()
start_server = websockets.serve(connect_client, "127.0.0.1", 8000, ping_timeout=None)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()


orders = {}
for order in unprepared_orders:
    api_key_name = order['api_key_name']
    sub = order['sub']
    if api_key_name not in orders.keys():
        orders[api_key_name] = {}
    if sub not in orders[api_key_name].keys():
        orders[api_key_name][sub] = {'limit': [], 'stop market': []}
    orders[api_key_name][sub][order['type']].append(order['order'])

for api_key_name, sub_names in orders.items():
    for sub_name in sub_names.keys():
        type_orders = {'stop': orders[api_key_name][sub_name]['stop market'],
                       'limit': orders[api_key_name][sub_name]['limit']}
        for _type, _orders in type_orders.items():
            type_type = 'limit'
            if _type == 'stop':
                type_type = 'stop market'
            if _orders:
                api_id = str(_orders[0]['api_id'])
                info = api_id + sub_name + _type
                button = f"<input type=\"button\" id=\"button_{info}\" value = \"update\" style=\"color:red\"" \
                         " onclick=\"update_table_row('" + api_id + "','" + 'MARKET' \
                         + "','" + sub_name + "','" + _type + "')\"/>"
                for order in _orders:
                    del order['api_id']
                orders[api_key_name][sub_name][type_type] = {'button': button,
                                                             'orders': _orders}
                orders[api_key_name][sub_name][type_type]['orders'] = f'<span id="{info}">' + \
                                                                      template('make_table', {
                                                                          'cols_rows': _orders}) + '</span>'
            elif not _orders:
                orders[api_key_name][sub_name][type_type] = {'button': '',
                                                             'orders': []}
