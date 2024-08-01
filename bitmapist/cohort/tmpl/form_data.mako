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
            As percent:
            <select name="as_percent">
                <option value="1" ${ 'selected="selected"' if as_percent else '' }>Yes</option>
                <option value="0" ${ 'selected="selected"' if not as_percent else '' }>No</option>
            </select>
        </dd>

        <dd>
            Number of results:
            <select name="num_results">
                <option value="7" ${ 'selected="selected"' if num_results == 7 else '' }>7</option>
                <option value="28" ${ 'selected="selected"' if num_results == 28 else '' }>28</option>
                <option value="31" ${ 'selected="selected"' if num_results == 31 else '' }>31</option>
                <option value="" disabled="disabled">----</option>
                <option value="12" ${ 'selected="selected"' if num_results == 12 else '' }>12</option>
                <option value="24" ${ 'selected="selected"' if num_results == 24 else '' }>24</option>
                <option value="" disabled="disabled">----</option>
                <option value="4" ${ 'selected="selected"' if num_results == 4 else '' }>4</option>
                <option value="52" ${ 'selected="selected"' if num_results == 52 else '' }>52</option>
                <option value="104" ${ 'selected="selected"' if num_results == 104 else '' }>104</option>
            </select>
        </dd>

        <dd>
            Number of rows:
            <select name="num_of_rows">
                <option value="3" ${ 'selected="selected"' if num_of_rows == 3 else '' }>3</option>
                <option value="6" ${ 'selected="selected"' if num_of_rows == 6 else '' }>6</option>
                <option value="12" ${ 'selected="selected"' if num_of_rows == 12 else '' }>12</option>
                <option value="24" ${ 'selected="selected"' if num_of_rows == 24 else '' }>24</option>
                <option value="48" ${ 'selected="selected"' if num_of_rows == 48 else '' }>48</option>
            </select>
        </dd>

        <dd>
            Start date:
            <input name="start_date" type="date" value="${ start_date if start_date else "" | h }" />
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
