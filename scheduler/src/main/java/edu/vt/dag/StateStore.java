package edu.vt.dag;

import java.util.function.Function;

/** One transaction-shaped command includes record changes AND event append. No I/O in a command. */
public interface StateStore {
    <T> T command(Function<SchedulerState,T> command);
}
