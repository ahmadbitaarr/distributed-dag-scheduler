package edu.vt.dag;

import java.util.function.Function;

/** The sole MS2 backend. The single monitor serializes commands and snapshots. */
public final class MemoryStateStore implements StateStore {
    private final SchedulerState state=new SchedulerState();
    @Override public synchronized <T> T command(Function<SchedulerState,T> command) { return command.apply(state); }
}
