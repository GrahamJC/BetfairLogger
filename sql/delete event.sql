begin transaction;

delete
from	market_runner_order
where	market_id in (select id from market where event_id = 245);

update	market
set		last_book_id = null,
		last_prerace_book_id = null,
		last_inplay_book_id = null
where	event_id = 245;

delete
from	market_runner_book
where	market_book_id in (select id from market_book where market_id in (select id from market where event_id = 245));

delete
from	market_runner
where	market_id in (select id from market where event_id = 245);

delete
from	market_book
where	market_id in (select id from market where event_id = 245);

delete
from	market
where	event_id = 245;

delete
from	event
where	id = 245;

rollback;
