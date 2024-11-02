=========================
Fragmentation Random Test
=========================

FRT operation
^^^^^^^^^^^^^

Fragmentation Random Test generates and runs test cases in a loop in 4 stages:

Stage 1
-------

Stage 1 prepares the test case to be run.
It generates:

- a bitbuffer of a random length that represents a compressed packet.
  Since the compression is not part of the test, all bits are randomly selected as well.
- A fragmentation rule where all parameters are individually a randomly selected from all cases that SCHC supports

Stage 2
-------

Stage 2 runs the fragmentation procedure and injects random transmission errors.

- The procedure randomly decides at which times in the transmission the transmission errors are injected
- The error being injected might be a number of packets in a row or a black-out period, i.e. all packets in a direction or in both directions are dropped for a selected duration.
- whether the injection of errors should exceed the maximum number of retries in which case it sets the expected result as an abort, else it sets the expected result as a validation
- the test runs till both sides are complete or a simulated maximum time is reached

Stage 3
-------

Stage 3 validates the expected result is reached.
It checks:

- whether both sides ran to completion or if one side is still waiting or still has resources locked for this fragment
- whether an abort condition was reached on one side or both sides
- if the receiver did not abort, whether the bitbuffer is reassembled correctly up to the expected length (extra bits are ignored)

Stage 4
-------

Stage 4 logs the parameters of the test case, including:

- the generated rule and the timeline of events as experienced by the scheduler
- whether the test case resulted in the expected outcome
- whether the expected number of test cases where tried; if not a new test case is scheduled.


Hacking the Scheduler
^^^^^^^^^^^^^^^^^^^^^
