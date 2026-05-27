-- KEYS[1] = client:{id}:balance
-- ARGV[1] = cost
return redis.call('INCRBY', KEYS[1], ARGV[1])
