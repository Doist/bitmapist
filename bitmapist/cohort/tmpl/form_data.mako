<form action="${ action_url }" method="GET">
    <dl>
        <dt>People actions</dt>
            <dd>
            Show me people who 

            ${ render_options('select1', selections1, select1) }

            and then came back and

            ${ render_options('select2', selections2, select2) }

            </dd>

        <dt>Group by</dt>
            <dd>
            Group by 
            <select name="time_group">
                <option value="days" ${ 'selected="selected"' if time_group == 'days' else '' }>Days</option>
                <option value="weeks" ${ 'selected="selected"' if time_group == 'weeks' else '' }>Weeks</option>
                <option value="months" ${ 'selected="selected"' if time_group == 'months' else '' }>Months</option>
            </select>
            </dd>

        <dt><input type="submit" value="Show me results" /></dt>
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
