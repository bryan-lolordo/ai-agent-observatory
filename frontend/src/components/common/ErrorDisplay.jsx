/**
 * ErrorDisplay - Consistent error display with retry/back options
 * 
 * Provides standardized error UI for failed data fetches
 * across all story pages.
 * 
 * Uses BASE_THEME for neutral colors - no hardcoded grays!
 * Uses BASE_THEME.status.error for error styling
 */

import PageContainer from '../layout/PageContainer';
import BackButton from './BackButton';
import { BASE_THEME } from '../../utils/themeUtils';

export default function ErrorDisplay({ 
  error, 
  onRetry, 
  onBack, 
  backLabel = "Back to Overview",
  theme 
}) {
  return (
    <div className={`min-h-screen ${BASE_THEME.container.tertiary} p-8`}>
      <PageContainer>
        {onBack && (
          <BackButton onClick={onBack} label={backLabel} theme={theme} />
        )}
        
        <div className={`${BASE_THEME.status.error.bg} border ${BASE_THEME.status.error.border} rounded-lg p-6`}>
          <h2 className={`text-xl font-bold ${BASE_THEME.status.error.textBold} mb-2`}>
            Error Loading Data
          </h2>
          <p className={BASE_THEME.text.secondary}>{error}</p>
          
          {onRetry && (
            <button
              onClick={onRetry}
              className={`mt-4 px-4 py-2 ${BASE_THEME.status.error.bgSolid} ${BASE_THEME.status.error.bgSolidHover} text-white rounded-lg transition-colors`}
            >
              Retry
            </button>
          )}
        </div>
      </PageContainer>
    </div>
  );
}