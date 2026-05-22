import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import FilesPage from './pages/FilesPage';
import FileDataPage from './pages/FileDataPage';
import BalancesPage from './pages/BalancesPage';
import RegulatoryPage from './pages/RegulatoryPage';
import LoansDepositsPage from './pages/LoansDepositsPage';
import ToolsPage from './pages/ToolsPage';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<FilesPage />} />
          <Route path="/files" element={<FilesPage />} />
          <Route path="/file/:fileId" element={<FileDataPage />} />
          <Route path="/balances" element={<BalancesPage />} />
          <Route path="/regulatory" element={<RegulatoryPage />} />
          <Route path="/loans-deposits" element={<LoansDepositsPage />} />
          <Route path="/tools" element={<ToolsPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;