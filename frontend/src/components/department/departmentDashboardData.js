function asObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function asArray(value) {
  return Array.isArray(value)
    ? value.filter(item => item && typeof item === 'object' && !Array.isArray(item))
    : [];
}

export function normalizeDepartmentDashboardResponse(value) {
  const source = asObject(value);
  const suggestionData = asObject(source.suggestions);
  return {
    ...source,
    scope: asObject(source.scope),
    summary: asObject(source.summary),
    comparisons: asObject(source.comparisons),
    categories: asArray(source.categories),
    borrowing_trend: asArray(source.borrowing_trend),
    borrowing_by_category: asArray(source.borrowing_by_category),
    student_vs_faculty: asArray(source.student_vs_faculty),
    book_utilization: asArray(source.book_utilization),
    copy_status: asArray(source.copy_status),
    suggestion_demand: asArray(source.suggestion_demand),
    top_books: asArray(source.top_books),
    recent_suggestions: asArray(source.recent_suggestions),
    suggestions: { ...suggestionData, items: asArray(suggestionData.items) },
  };
}
