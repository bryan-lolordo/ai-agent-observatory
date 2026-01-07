/**
 * Loading Component
 *
 * Displays loading states with multiple variants optimized for dark theme.
 * - spinner: Simple spinning loader
 * - skeleton: Skeleton placeholder for content
 * - page: Full-page loading overlay
 *
 * UPDATED: Uses BASE_THEME - no hardcoded colors!
 */

import { BASE_THEME } from '../../utils/themeUtils';

/**
 * Spinner variant - Simple rotating circle
 */
function Spinner({ size = 'md', className = '' }) {
  const sizes = {
    sm: 'h-4 w-4 border-2',
    md: 'h-8 w-8 border-3',
    lg: 'h-12 w-12 border-4',
  };

  return (
    <div
      className={`inline-block animate-spin rounded-full border-solid border-current border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite] ${sizes[size]} ${className}`}
      role="status"
    >
      <span className="sr-only">Loading...</span>
    </div>
  );
}

/**
 * Skeleton variant - Animated placeholder
 */
function Skeleton({ className = '', variant = 'rectangle' }) {
  const variants = {
    rectangle: 'rounded',
    circle: 'rounded-full',
    text: 'rounded h-4',
  };

  return (
    <div
      className={`animate-pulse ${BASE_THEME.container.secondary} ${variants[variant]} ${className}`}
    />
  );
}

/**
 * Card skeleton - For loading story cards
 */
function CardSkeleton() {
  return (
    <div className={`rounded-lg border ${BASE_THEME.border.default} p-6 space-y-4 ${BASE_THEME.container.secondary}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <Skeleton className="w-12 h-12" variant="circle" />
          <div className="space-y-2">
            <Skeleton className="w-32 h-5" />
            <Skeleton className="w-48 h-3" />
          </div>
        </div>
        <Skeleton className="w-12 h-8" />
      </div>
      <div className="space-y-2">
        <Skeleton className="w-full h-3" />
        <Skeleton className="w-3/4 h-3" />
      </div>
    </div>
  );
}

/**
 * Table skeleton - For loading data tables
 */
function TableSkeleton({ rows = 5, columns = 4 }) {
  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex gap-4">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} className="h-6 flex-1" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div key={rowIdx} className="flex gap-4">
          {Array.from({ length: columns }).map((_, colIdx) => (
            <Skeleton key={colIdx} className="h-8 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

/**
 * KPI Card skeleton - For loading metric cards
 */
function KPICardSkeleton() {
  return (
    <div className={`rounded-lg border ${BASE_THEME.border.default} p-6 space-y-3 ${BASE_THEME.container.secondary}`}>
      <Skeleton className="w-24 h-4" />
      <Skeleton className="w-32 h-8" />
      <Skeleton className="w-20 h-3" />
    </div>
  );
}

/**
 * Page loading - Full page overlay with spinner
 */
function PageLoading({ message = 'Loading...' }) {
  return (
    <div className={`min-h-screen flex items-center justify-center ${BASE_THEME.container.tertiary}`}>
      <div className="text-center space-y-4">
        <Spinner size="lg" className={`mx-auto ${BASE_THEME.status.info.text}`} />
        <p className={`${BASE_THEME.text.muted} text-lg`}>{message}</p>
      </div>
    </div>
  );
}

/**
 * Inline loading - Small inline spinner with text
 */
function InlineLoading({ text = 'Loading...' }) {
  return (
    <div className={`flex items-center gap-2 ${BASE_THEME.text.muted}`}>
      <Spinner size="sm" />
      <span className="text-sm">{text}</span>
    </div>
  );
}

/**
 * Dashboard skeleton - For loading main dashboard
 */
function DashboardSkeleton() {
  return (
    <div className={`min-h-screen ${BASE_THEME.container.tertiary} p-8`}>
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="space-y-2">
          <Skeleton className="w-64 h-10" />
          <Skeleton className="w-96 h-5" />
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <KPICardSkeleton />
          <KPICardSkeleton />
          <KPICardSkeleton />
        </div>

        {/* Story Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6, 7, 8].map(i => (
            <CardSkeleton key={i} />
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Story page skeleton - For loading individual story pages
 */
export function StoryPageSkeleton() {
  return (
    <div className={`min-h-screen ${BASE_THEME.container.tertiary} p-8`}>
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Breadcrumb */}
        <Skeleton className="w-48 h-5" />

        {/* Header */}
        <div className="space-y-3">
          <Skeleton className="w-64 h-10" />
          <Skeleton className="w-96 h-5" />
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <KPICardSkeleton />
          <KPICardSkeleton />
          <KPICardSkeleton />
          <KPICardSkeleton />
        </div>

        {/* Table */}
        <div className={`rounded-lg border ${BASE_THEME.border.default} p-6 ${BASE_THEME.container.secondary}`}>
          <Skeleton className="w-48 h-6 mb-6" />
          <TableSkeleton rows={8} columns={6} />
        </div>
      </div>
    </div>
  );
}

/**
 * Default export - Basic loading component
 */
export default function Loading({
  variant = 'spinner',
  size = 'md',
  fullPage = false,
  message,
  ...props
}) {
  if (fullPage) {
    return <PageLoading message={message} />;
  }

  if (variant === 'spinner') {
    return <Spinner size={size} {...props} />;
  }

  if (variant === 'skeleton') {
    return <Skeleton {...props} />;
  }

  return <Spinner size={size} {...props} />;
}

// Export all variants
export {
  Spinner,
  Skeleton,
  CardSkeleton,
  TableSkeleton,
  KPICardSkeleton,
  PageLoading,
  InlineLoading,
  DashboardSkeleton,
};
