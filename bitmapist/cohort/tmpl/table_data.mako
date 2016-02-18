<style>
.cohort_table {
    width: 1250px !important;
	font-family: sans-serif;
}

.cohort_table .entry {
    width: 6%;
}

.cohort_table td, .cohort_table th {
    padding: 5px 0;
    text-align: center;
    border-right: 1px solid #aaa;
}

.cohort_table td {
    border-bottom: 1px solid #aaa;
}



.cohort_table .date {
    display: inline-block;
    width: 125px;
}

.cohort_table .total_count {
    display: inline-block;
    width: 50px;
}

.cohort_table td.avg_row {
    border-top: 1px solid #aaa !important;
}

</style>

<table class="cohort_table" cellpadding="0" cellspacing="0">
    <tr>
        <th width="200"></th>
        %for i in range(0, num_of_rows+1):
            <th class="entry">${ i }</th>
        %endfor
    </tr>

    %for row_data in dates_data:
        <tr>
            <td> 
                <div class="date">
                    %if time_group == 'months':
                        ${ row_data[0].strftime('%d %b') }
                    %elif time_group == 'weeks':
                        ${ row_data[0].strftime('Week %U, %d %b') }
                    %elif time_group == 'years':
                        ${ row_data[0].strftime('%Y') }
                    %else:
                        ${ row_data[0].strftime('%d %b, %Y') }
                    %endif
                </div>

                ## Total count
                <div class="total_count">${ row_data[1] }</div>
            </td>

            %for i in range(2, num_of_rows+3):
                <%
                prct = row_data[i]
                %>

                %if prct != '':
                    %if as_precent:
                        <%
                        color = 'hsla(200, 100%%, 0%%, %s);' % (round(float(prct/100)+0.5, 1))
                        %>
                        <td style="background-color: hsla(200, 80%, 50%, ${ round(float(prct/100), 1) }); color: ${ color }">
                            ${ round(prct, 2) }%
                        </td>
                    %else:
                        <td>
                            ${ int(prct) }
                        </td>
                    %endif
                %else:
                    <td></td>
                %endif
            %endfor
        </tr>
    %endfor

    <tr>
        <td class="avg_row"></td>
        %for i in range(2, num_of_rows+3):
            <%
                cnts = 0
                total = 0.0
                for row_data in dates_data:
                    prct = row_data[i]
                    if prct:
                        cnts += 1
                        total += prct

                if cnts > 0:
                    avg = total / cnts
                else:
                    avg = 0
            %>

            <td class="avg_row">
                %if as_precent:
                    ${ round(avg, 2) }%
                %else:
                    ${ int(avg) }
                %endif
            </td>
        %endfor
    </tr>
</table>

<div style="padding-top: 20px;">
    <a href="#" target="_blank" onclick="window.open(location.href + '&export_csv=1'); return false;">Export as CSV</a>
</div>
