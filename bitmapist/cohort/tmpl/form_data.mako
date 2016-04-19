<style>
.cohort_form dd {
    display: inline-block;
    margin-right: 5px;
}

.cohort_form select {
    max-width: 150px;
}
</style>

<form action="${ action_url }" method="GET" class="cohort_form">
    <dl>
        <dd>
            Show me people who
            ${ render_options('select1', selections1, select1) }
            AND
            ${ render_options('select1b', selections1b, select1b) }
            and then came back to
            ${ render_options('select2', selections2, select2) }
            AND
            ${ render_options('select2b', selections2b, select2b) }
        </dd>

    </dl>

    <dl>
        <dd>
            Group By:
            <select name="time_group">
                <option value="days" ${ 'selected="selected"' if time_group == 'days' else '' }>Days</option>
                <option value="weeks" ${ 'selected="selected"' if time_group == 'weeks' else '' }>Weeks</option>
                <option value="months" ${ 'selected="selected"' if time_group == 'months' else '' }>Months</option>
                <option value="years" ${ 'selected="selected"' if time_group == 'years' else '' }>Years</option>
            </select>
        </dd>

        <dd>
            As precent:
            <select name="as_precent">
                <option value="1" ${ 'selected="selected"' if as_precent else '' }>Yes</option>
                <option value="0" ${ 'selected="selected"' if not as_precent else '' }>No</option>
            </select>
        </dd>

        <dd>
            Number of results:
            <select name="num_results">
                <option value="5" ${ 'selected="selected"' if num_results == 5 else '' }>5</option>
                <option value="25" ${ 'selected="selected"' if num_results == 25 else '' }>25</option>
                <option value="50" ${ 'selected="selected"' if num_results == 50 else '' }>50</option>
                <option value="100" ${ 'selected="selected"' if num_results == 100 else '' }>100</option>
            </select>
        </dd>

        <dd>
            Number of rows:
            <select name="num_of_rows">
                <option value="12" ${ 'selected="selected"' if num_of_rows == 12 else '' }>12</option>
                <option value="24" ${ 'selected="selected"' if num_of_rows == 24 else '' }>24</option>
                <option value="48" ${ 'selected="selected"' if num_of_rows == 48 else '' }>48</option>
            </select>
        </dd>
    </dl>

    <dl>
        <dd>
            <input type="submit" value="Show me results" />
        </dd>
    </dl>
</form>

<%def name="render_options(select_name, selections, current_selection)">
    <select name="${ select_name }">
        %for option in selections:
            %if option == '---':
                <option value="" disabled="disabled">----</option>
            %elif current_selection == option[1]:
                <option value="${ option[1] }" selected="selected">${ option[0] }</option>
            %else:
                <option value="${ option[1] }">${ option[0] }</option>
            %endif
        %endfor
    </select>
</%def>
