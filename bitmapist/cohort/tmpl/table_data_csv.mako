Date,Total,${ ",".join(str(i) for i in range(0, num_of_rows+1)) }
%for row_data in dates_data:
<%
if time_group == 'months':
    date = row_data[0].strftime('%d %b')
elif time_group == 'weeks':
    date = row_data[0].strftime('Week %U %d %b')
elif time_group == 'years':
    date = row_data[0].strftime('%Y')
else:
    date = row_data[0].strftime('%d %b %Y')

total_count = row_data[1]

day_results = []
for i in range(2, num_of_rows+3):
    prct = row_data[i]
    if prct == '':
        day_results.append('')
    else:
        if as_percent:
            day_results.append(str(round(prct, 2)))
        else:
            day_results.append(str(int(prct)))
%>\
${ date },${ total_count },${ ','.join(day_results) }
%endfor
