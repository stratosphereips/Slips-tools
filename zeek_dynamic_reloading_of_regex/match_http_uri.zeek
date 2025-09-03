@load base/protocols/http

module RegexMonitor;

export {
    # CSV schema
    # keep in mind that Zeek uses these records to determine the names of the fields it expects to find in your CSV file
    type Idx: record {
        regex: pattern;
    };

    type Val: record {
        description: string;
    };

    # Store compiled regex -> description dict
    global regex_table: table[pattern] of Val = table();


}

# incase you want to do something with entries
# tap into events of input-framework
event line(description: Input::TableDescription, tpe: Input::Event,
    left: Idx, right: Val)
    {
    local desc = right$description;

    if ( tpe == Input::EVENT_NEW )
        {
        print fmt ("Added regex %s description %s", left$regex, right$description );
        }
    if ( tpe == Input::EVENT_CHANGED )
        {
        print fmt ("Changed Entry! regex %s description %s", left$regex, right$description );
        }
    if ( tpe == Input::EVENT_REMOVED )
        {
        print fmt ("Removed regex %s description %s", left$regex, right$description );
        }
    }



# Initializes the Input framework to read the CSV file
event zeek_init()
    {
    Input::add_table([$source="regex.csv",
                      $name="regex_patterns",
                      $destination=regex_table,
                      $idx=Idx,
                      $val=Val,
                      $mode=Input::REREAD,
                      $ev=line,
                      ]);
    }




# --- HTTP Matching ---
event http_request(c: connection, method: string, original_URI: string, unescaped_URI: string, version: string)
    {
        # Iterate over the table of compiled regex patterns.
        for ( re in regex_table )
            {
            # Perform the regex match.
            if (  re in original_URI )
                {
                print fmt("Wohoo regex %s (%s) matched this uri: %s",
                          re, regex_table[re], original_URI);
                }
            }
    }
