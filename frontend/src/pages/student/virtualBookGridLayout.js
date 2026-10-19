export const VIRTUAL_GRID_GAP = 16;
export const BOOK_COVER_MAX_WIDTH = 180;
export const BOOK_COVER_WIDTH_RATIO = 0.58;
export const CARD_HEADER_HEIGHT = 52;
export const CARD_STATUS_HEIGHT = 49;
export const CARD_BORDER_HEIGHT = 2;
export const EXPANDED_DETAILS_HEIGHT = 190;

export function getVirtualBookGridLayout(width, itemCount, expandedRows = {}) {
  const availableWidth = Math.max(1, Number(width) || 1);
  const columns = availableWidth < 620 ? 1 : availableWidth < 960 ? 2 : availableWidth < 1280 ? 3 : 4;
  const cardWidth = Math.max(1, (availableWidth - VIRTUAL_GRID_GAP * (columns - 1)) / columns);
  const coverWidth = Math.min(BOOK_COVER_MAX_WIDTH, cardWidth * BOOK_COVER_WIDTH_RATIO);
  const coverHeight = coverWidth * 1.5;
  const baseCardHeight = Math.ceil(CARD_HEADER_HEIGHT + coverHeight + CARD_STATUS_HEIGHT + CARD_BORDER_HEIGHT);
  const totalRows = Math.ceil(Math.max(0, Number(itemCount) || 0) / columns);
  const rowHeights = Array.from({ length: totalRows }, (_, row) => (
    baseCardHeight + (expandedRows[row] ? EXPANDED_DETAILS_HEIGHT : 0) + VIRTUAL_GRID_GAP
  ));
  const rowTops = [];
  let spacerHeight = 0;
  for (const height of rowHeights) {
    rowTops.push(spacerHeight);
    spacerHeight += height;
  }
  return { columns, cardWidth, coverWidth, coverHeight, baseCardHeight, rowHeights, rowTops, spacerHeight };
}
