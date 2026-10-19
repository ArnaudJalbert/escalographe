import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { LanguageProvider, useLanguage } from './i18n'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { EscalatorDetail } from './pages/EscalatorDetail'
import { StationDetail } from './pages/StationDetail'
import { About } from './pages/About'

function NotFound() { const { t } = useLanguage(); return <div className="page-wrap py-24"><h1 className="text-4xl font-bold">{t("That stop isn't on the map.")}</h1><a className="text-link mt-6 inline-block" href="/">{t('Return to the atlas →')}</a></div> }
export default function App() {
  const [queryClient] = useState(() => new QueryClient({ defaultOptions: { queries: { staleTime: 60_000, refetchInterval: 300_000, retry: 1 } } }))
  return <LanguageProvider><QueryClientProvider client={queryClient}><BrowserRouter><Layout><Routes>
    <Route path="/" element={<Dashboard />} />
    <Route path="/escalators/:id" element={<EscalatorDetail />} />
    <Route path="/stations/:id" element={<StationDetail />} />
    <Route path="/about" element={<About />} />
    <Route path="*" element={<NotFound />} />
  </Routes></Layout></BrowserRouter></QueryClientProvider></LanguageProvider>
}
