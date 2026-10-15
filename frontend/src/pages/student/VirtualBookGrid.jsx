import { useEffect, useMemo, useRef, useState } from 'react';

const ROW_HEIGHT = 250;
const VIEWPORT_HEIGHT = 600;
const OVERSCAN = 2;

export default function VirtualBookGrid({ items, renderItem }) {
  const viewportRef = useRef(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [width, setWidth] = useState(1000);
  const [height, setHeight] = useState(VIEWPORT_HEIGHT);

  useEffect(() => {
    const element = viewportRef.current;
    if (!element) return undefined;
    const measure = () => {
      setWidth(element.clientWidth || 1000);
      setHeight(element.clientHeight || VIEWPORT_HEIGHT);
    };
    measure();
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(measure);
    observer?.observe(element);
    return () => observer?.disconnect();
  }, []);

  const columns = width < 620 ? 1 : width < 960 ? 2 : 3;
  const totalRows = Math.ceil(items.length / columns);
  const range = useMemo(() => {
    const first = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
    const last = Math.min(totalRows, Math.ceil((scrollTop + height) / ROW_HEIGHT) + OVERSCAN);
    return { first, last };
  }, [height, scrollTop, totalRows]);

  return (
    <div
      ref={viewportRef}
      className="virtual-book-viewport"
      role="list"
      aria-label="Book search results"
      onScroll={event => setScrollTop(event.currentTarget.scrollTop)}
    >
      <div className="virtual-book-spacer" style={{ height: totalRows * ROW_HEIGHT }}>
        {Array.from({ length: range.last - range.first }, (_, offset) => {
          const row = range.first + offset;
          const start = row * columns;
          return (
            <div
              className="virtual-book-row"
              key={`row-${row}`}
              style={{ top: row * ROW_HEIGHT, gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
            >
              {items.slice(start, start + columns).map((item, column) => renderItem(item, start + column, items.length))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
