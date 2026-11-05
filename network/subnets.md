# Task 5: Subnet allocation for 10.20.0.0/16

Method: sort requirements largest to smallest, start at 10.20.0.0, place each subnet immediately after the previous one,
and pick the smallest prefix p with 2^(32-p) - 2 >= hosts needed.

| Subnet     | Hosts needed | Prefix | Network address | Usable host range         | Broadcast    | Usable hosts |
|------------|--------------|--------|-----------------|---------------------------|--------------|--------------|
| app        | 1,000        | /22    | 10.20.0.0       | 10.20.0.1 - 10.20.3.254   | 10.20.3.255  | 1,022        |
| public     | 250          | /24    | 10.20.4.0       | 10.20.4.1 - 10.20.4.254   | 10.20.4.255  | 254          |
| data       | 100          | /25    | 10.20.5.0       | 10.20.5.1 - 10.20.5.126   | 10.20.5.127  | 126          |
| management | 20           | /27    | 10.20.5.128     | 10.20.5.129 - 10.20.5.158 | 10.20.5.159  | 30           |

## Working

- app: /23 gives 2^9 - 2 = 510 (too few); /22 gives 2^10 - 2 = 1,022 (fits). Block size 1,024 addresses: 10.20.0.0 - 10.20.3.255.
- public: /25 gives 126 (too few); /24 gives 2^8 - 2 = 254 (fits). Starts at 10.20.4.0 (right after 10.20.3.255).
- data: /26 gives 62 (too few); /25 gives 2^7 - 2 = 126 (fits). Starts at 10.20.5.0.
- management: /28 gives 14 (too few); /27 gives 2^5 - 2 = 30 (fits). Starts at 10.20.5.128 (right after 10.20.5.127).

## NACL explanation (fill in your own words; draft points)

1. A NACL is stateless: it does not remember that an inbound request was allowed, so the reply packet is judged
   on its own against the outbound rules (and a client's inbound replies against the inbound rules). Replies go to the
   client's ephemeral port (1024-65535), so we need explicit rules for that range in both directions.
2. Rules are evaluated from the lowest number upward and the first match wins. The deny for 198.51.100.0/24 is rule 50,
   lower than the allow rules for 80/443 (100/110). If it were numbered higher, TCP 443 from 198.51.100.9 would match
   the allow rule first and the abusive range would get through.
