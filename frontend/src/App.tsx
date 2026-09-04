import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { Toaster } from '@/components/ui/Toaster';
import { Layout } from '@/layout/Layout';
import { CommandCenter } from '@/pages/CommandCenter';
import { TrustProfiles } from '@/pages/TrustProfiles';
import { UserProfile } from '@/pages/UserProfile';
import { RiskIntelligence } from '@/pages/RiskIntelligence';
import { Investigations } from '@/pages/Investigations';
import { Payments } from '@/pages/Payments';
import { Ledger } from '@/pages/Ledger';
import { ModelLab } from '@/pages/ModelLab';
import { Developers } from '@/pages/Developers';
import { Verification } from '@/pages/Verification';
import { AICopilot } from '@/pages/AICopilot';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      gcTime: 1000 * 60 * 30,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<CommandCenter />} />
            <Route path="/trust" element={<TrustProfiles />} />
            <Route path="/trust/:userId" element={<UserProfile />} />
            <Route path="/risk" element={<RiskIntelligence />} />
            <Route path="/investigations/:eventId" element={<Investigations />} />
            <Route path="/payments" element={<Payments />} />
            <Route path="/ledger/:paymentId" element={<Ledger />} />
            <Route path="/model-lab" element={<ModelLab />} />
            <Route path="/copilot" element={<AICopilot />} />
            <Route path="/developers" element={<Developers />} />
            <Route path="/verification" element={<Verification />} />
          </Routes>
        </Layout>
        <Toaster />
        <ReactQueryDevtools initialIsOpen={false} />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;