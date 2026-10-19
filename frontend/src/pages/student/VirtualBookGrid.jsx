import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getVirtualBookGridLayout, VIRTUAL_GRID_GAP } from './virtualBookGridLayout';

const VIEWPORT_HEIGHT = 600;
const OVERSCAN = 2;

const firstRowAfterOffset = (layout, offset) => {
  let low = 0;
  let high = layout.rowHeights.length;
  while (low < high) {
    const middle = Math.floor((low + high) / 2);
    if (layout.rowTops[middle] + layout.rowHeights[middle] <= offset) low = middle + 1;
    else high = middle;
  }
  return low;
};

export default function VirtualBookGrid({ items, renderItem }) {
  const canvasRef = useRef(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [width, setWidth] = useState(1000);
  const [height, setHeight] = useState(VIEWPORT_HEIGHT);
  const [expandedItems, setExpandedItems] = useState({});

  useEffect(() => {
    setExpandedItems({});
  }, [items]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const updatePosition = () => setScrollTop(window.scrollY || document.documentElement.scrollTop || 0);
    const measure = () => {
      setWidth(canvas.clientWidth || 1000);
      setHeight(window.innerHeight || VIEWPORT_HEIGHT);
      updatePosition();
    };
    measure();
    window.addEventListener('scroll', updatePosition, { passive: true });
    window.addEventListener('resize', measure);
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(measure);
    observer?.observe(canvas);
    return () => {
      window.removeEventListener('scroll', updatePosition);
      window.removeEventListener('resize', measure);
      observer?.disconnect();
    };
  }, []);

  const baseLayout = useMemo(() => getVirtualBookGridLayout(width, items.length), [width, items.length]);
  const expandedRows = useMemo(() => Object.keys(expandedItems).reduce((rows, index) => {
    if (expandedItems[index]) rows[Math.floor(Number(index) / baseLayout.columns)] = true;
    return rows;
  }, {}), [baseLayout.columns, expandedItems]);
  const layout = useMemo(
    () => getVirtualBookGridLayout(width, items.length, expandedRows),
    [expandedRows, items.length, width],
  );
  const setItemExpanded = useCallback((index, expanded) => {
    setExpandedItems(current => {
      if (Boolean(current[index]) === expanded) return current;
      const next = { ...current };
      if (expanded) next[index] = true;
      else delete next[index];
      return next;
    });
  }, []);

  const canvasTop = canvasRef.current && typeof window !== 'undefined'
    ? canvasRef.current.getBoundingClientRect().top + window.scrollY
    : 0;
  const visibleTop = Math.max(0, scrollTop - canvasTop);
  const range = useMemo(() => {
    const firstVisible = firstRowAfterOffset(layout, visibleTop);
    const afterLastVisible = firstRowAfterOffset(layout, visibleTop + height);
    const first = Math.max(0, firstVisible - OVERSCAN);
    const last = Math.min(layout.rowHeights.length, afterLastVisible + OVERSCAN + 1);
    return { first, last };
  }, [height, layout, visibleTop]);

  return (
    <div
      ref={canvasRef}
      className="virtual-book-viewport"
      role="list"
      aria-label="Book search results"
    >
      <div className="virtual-book-spacer" style={{ height: layout.spacerHeight }}>
        {Array.from({ length: Math.max(0, range.last - range.first) }, (_, offset) => {
          const row = range.first + offset;
          const start = row * layout.columns;
          const rowHeight = layout.rowHeights[row] - VIRTUAL_GRID_GAP;
          return (
            <div
              className="virtual-book-row"
              key={`row-${row}`}
              style={{
                top: layout.rowTops[row],
                height: rowHeight,
                gridTemplateColumns: `repeat(${layout.columns}, minmax(0, 1fr))`,
              }}
            >
              {items.slice(start, start + layout.columns).map((item, column) => {
                const index = start + column;
                return renderItem(item, index, items.length, expanded => setItemExpanded(index, expanded), Boolean(expandedItems[index]));
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}
