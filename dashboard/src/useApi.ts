import { useCallback, useEffect, useState } from "react";
import { getJson } from "./api";

export interface Loaded<T> {
  data: T | undefined;
  error: string | undefined;
  reload: () => void;
}

interface State<T> {
  path: string;
  data?: T;
  error?: string;
}

// How long to wait before loading again: a fixed number of milliseconds, or one
// worked out from what was loaded last. Zero means don't load again.
export type Refresh<T> = number | ((data: T | undefined) => number);

export function useApi<T>(path: string, refresh: Refresh<T>): Loaded<T> {
  const [state, setState] = useState<State<T>>({ path });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let live = true;
    let last: T | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const schedule = () => {
      const wait = typeof refresh === "number" ? refresh : refresh(last);
      if (live && wait > 0) timer = setTimeout(load, wait);
    };
    const load = () => {
      getJson<T>(path).then(
        (data) => {
          last = data;
          if (live) setState({ path, data });
          schedule();
        },
        (error: unknown) => {
          if (live)
            setState({
              path,
              data: last,
              error: error instanceof Error ? error.message : String(error),
            });
          schedule();
        },
      );
    };
    load();
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [path, refresh, tick]);

  const reload = useCallback(() => {
    setTick((t) => t + 1);
  }, []);
  const current = state.path === path;
  return {
    data: current ? state.data : undefined,
    error: current ? state.error : undefined,
    reload,
  };
}
