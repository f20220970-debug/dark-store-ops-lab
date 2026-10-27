"""Picker staffing with a queueing model (Erlang C, M/M/c).

Orders arrive at random (Poisson) and each picker handles one order at a time. For each hour,
find the fewest pickers so that at least SLA_TARGET of orders start picking within
SLA_WAIT_SECONDS. This is the standard call-centre staffing formula applied to picking.
"""
import math

import config as C


def erlang_c(arrivals_per_s: float, service_s: float, servers: int) -> float:
    """Probability an arriving order has to wait (all pickers busy)."""
    a = arrivals_per_s * service_s                      # offered load in Erlangs
    if servers <= a:
        return 1.0
    top = (a ** servers / math.factorial(servers)) * (servers / (servers - a))
    bottom = sum(a ** k / math.factorial(k) for k in range(servers)) + top
    return top / bottom


def prob_wait_over(arrivals_per_s: float, service_s: float, servers: int, t: float) -> float:
    pw = erlang_c(arrivals_per_s, service_s, servers)
    if pw >= 1.0:
        return 1.0
    return pw * math.exp(-(servers / service_s - arrivals_per_s) * t)


def pickers_needed(orders_per_hour: float, service_s: float,
                   wait_s: float = C.SLA_WAIT_SECONDS, target: float = C.SLA_TARGET) -> int:
    lam = orders_per_hour / 3600
    c = max(1, math.ceil(lam * service_s))
    while prob_wait_over(lam, service_s, c, wait_s) > 1 - target:
        c += 1
    return c
