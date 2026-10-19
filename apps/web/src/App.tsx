import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { EscalatorDetail } from './pages/EscalatorDetail'
import { StationDetail } from './pages/StationDetail'
import { About } from './pages/About'

export default function App() {
  const [queryClient] = useState(() => new QueryClient({ defaultOptions: { queries: { staleTime: 60_000, refetchInterval: 300_000, retry: 1 } } }))
  return <QueryClientProvider client={queryClient}><BrowserRouter><Layout><Routes>
    <Route path="/" element={<Dashboard />} />
    <Route path="/escalators/:id" element={<EscalatorDetail />} />
    <Route path="/stations/:id" element={<StationDetail />} />
    <Route path="/about" element={<About />} />
    <Route path="*" element={<div className="page-wrap py-24"><h1 className="text-4xl font-bold">That stop isn't on the map.</h1><a className="text-link mt-6 inline-block" href="/">Return to the atlas →</a></div>} />
  </Routes></Layout></BrowserRouter></QueryClientProvider>
}
