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

export function useApi<T>(path: string, refreshMs: number): Loaded<T> {
  const [state, setState] = useState<State<T>>({ path });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let live = true;
    const load = () => {
      getJson<T>(path).then(
        (data) => {
          if (live) setState({ path, data });
        },
        (error: unknown) => {
          if (live)
            setState((old) => ({
              path,
              data: old.path === path ? old.data : undefined,
              error: error instanceof Error ? error.message : String(error),
            }));
        },
      );
    };
    load();
    const timer = refreshMs > 0 ? setInterval(load, refreshMs) : undefined;
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [path, refreshMs, tick]);

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
