% A campus robot can carry one package at a time.
package(books, mailroom, library).
package(lab_supplies, mailroom, lab).

road(mailroom, library).
road(mailroom, cafeteria).
road(library, lab).
road(cafeteria, lab).

% Scenarios remove roads from the same campus map.
blocked(normal, _, _) :- fail.
blocked(detour, mailroom, library).
blocked(disconnected, library, lab).
blocked(disconnected, cafeteria, lab).

connected(Scenario, From, To) :-
    (road(From, To); road(To, From)),
    \+ blocked(Scenario, From, To),
    \+ blocked(Scenario, To, From).

% State: robot location, carried package (or none), package positions.
initial(state(mailroom, none, [at(books, mailroom), at(lab_supplies, mailroom)])).

goal(state(_, none, Positions)) :-
    forall(package(Name, _, Destination), member(at(Name, Destination), Positions)).

action(Scenario, state(From, Carry, Positions), move(From, To),
       state(To, Carry, Positions)) :-
    connected(Scenario, From, To).
action(_, state(Place, none, Positions), pickup(Name, Place),
       state(Place, Name, Remaining)) :-
    select(at(Name, Place), Positions, Remaining),
    package(Name, _, Destination),
    Place \= Destination.
action(_, state(Place, Name, Positions), dropoff(Name, Place),
       state(Place, none, [at(Name, Place)|Positions])) :-
    Name \= none,
    package(Name, _, Place).

% Breadth-first search finds a shortest plan and avoids repeated states.
plan(Scenario, Plan) :-
    memberchk(Scenario, [normal, detour, disconnected]),
    initial(Start),
    search(Scenario, [node(Start, [])], [Start], Reversed),
    reverse(Reversed, Plan).

search(_, [node(State, Plan)|_], _, Plan) :- goal(State), !.
search(Scenario, [node(State, Plan)|Queue], Seen, Result) :-
    findall(node(Next, [Action|Plan]),
            (action(Scenario, State, Action, Next), \+ memberchk(Next, Seen)),
            Candidates),
    add_unseen(Candidates, Seen, NewSeen, Fresh),
    append(Queue, Fresh, NewQueue),
    search(Scenario, NewQueue, NewSeen, Result).

add_unseen([], Seen, Seen, []).
add_unseen([node(State, Plan)|Rest], Seen, FinalSeen, Fresh) :-
    ( memberchk(State, Seen) ->
        add_unseen(Rest, Seen, FinalSeen, Fresh)
    ; Fresh = [node(State, Plan)|More],
      add_unseen(Rest, [State|Seen], FinalSeen, More)
    ).

% Run demo(normal), demo(detour), or demo(disconnected).
demo(Scenario) :-
    ( \+ memberchk(Scenario, [normal, detour, disconnected]) ->
        format('Unknown scenario: ~w~n', [Scenario]), fail
    ; plan(Scenario, Plan) ->
        format('Scenario: ~w~n', [Scenario]),
        print_steps(Plan, 1),
        writeln('All packages delivered.')
    ; format('Scenario: ~w~nNo delivery plan exists.~n', [Scenario])
    ).

print_steps([], _).
print_steps([Action|Rest], Number) :-
    format('~d. ', [Number]),
    print_action(Action),
    Next is Number + 1,
    print_steps(Rest, Next).

print_action(move(From, To)) :- format('Move from ~w to ~w~n', [From, To]).
print_action(pickup(Name, Place)) :- format('Pick up ~w at ~w~n', [Name, Place]).
print_action(dropoff(Name, Place)) :- format('Drop off ~w at ~w~n', [Name, Place]).

% The website supplies roads and packages as JSON through standard input.
:- use_module(library(http/json)).

web_plan :-
    json_read_dict(current_input, Data, [value_string_as(atom)]),
    maplist(web_road, Data.roads, Roads),
    maplist(web_package, Data.packages, Packages),
    findall(at(Name, Start), member(pkg(Name, Start, _), Packages), Positions),
    Start = state(mailroom, none, Positions),
    ( web_search(Roads, Packages, [node(Start, [])], [Start], Reversed) ->
        reverse(Reversed, Plan),
        maplist(action_json, Plan, Actions),
        json_write_dict(current_output, _{found:true, actions:Actions})
    ; json_write_dict(current_output, _{found:false, actions:[]})
    ),
    nl.

web_road(Dict, road(Dict.from, Dict.to)).
web_package(Dict, pkg(Dict.name, Dict.start, Dict.destination)).

web_goal(Packages, state(_, none, Positions)) :-
    forall(member(pkg(Name, _, Destination), Packages),
           member(at(Name, Destination), Positions)).

web_action(Roads, _, state(From, Carry, Positions), move(From, To),
           state(To, Carry, Positions)) :-
    (member(road(From, To), Roads); member(road(To, From), Roads)).
web_action(_, Packages, state(Place, none, Positions), pickup(Name, Place),
           state(Place, Name, Remaining)) :-
    select(at(Name, Place), Positions, Remaining),
    member(pkg(Name, _, Destination), Packages),
    Place \= Destination.
web_action(_, Packages, state(Place, Name, Positions), dropoff(Name, Place),
           state(Place, none, [at(Name, Place)|Positions])) :-
    Name \= none,
    member(pkg(Name, _, Place), Packages).

web_search(_, Packages, [node(State, Plan)|_], _, Plan) :-
    web_goal(Packages, State),
    !.
web_search(Roads, Packages, [node(State, Plan)|Queue], Seen, Result) :-
    findall(node(Next, [Action|Plan]),
            (web_action(Roads, Packages, State, Action, Next),
             \+ memberchk(Next, Seen)),
            Candidates),
    add_unseen(Candidates, Seen, NewSeen, Fresh),
    append(Queue, Fresh, NewQueue),
    web_search(Roads, Packages, NewQueue, NewSeen, Result).

action_json(move(From, To), _{type:move, from:From, to:To}).
action_json(pickup(Name, Place), _{type:pickup, package:Name, location:Place}).
action_json(dropoff(Name, Place), _{type:dropoff, package:Name, location:Place}).
