import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/upload': 'http://localhost:8000',
      '/upload-accounts': 'http://localhost:8000',
      '/upload-initial-balances': 'http://localhost:8000',
      '/upload-transactions': 'http://localhost:8000',
      '/upload-loans': 'http://localhost:8000',
      '/upload-deposits': 'http://localhost:8000',
      '/upload-capital': 'http://localhost:8000',
      '/upload-exchange-rates': 'http://localhost:8000',
      '/upload-bonds': 'http://localhost:8000',
      '/files': 'http://localhost:8000',
      '/file-data': 'http://localhost:8000',
      '/corrections': 'http://localhost:8000',
      '/apply-corrections': 'http://localhost:8000',
      '/correction-logs': 'http://localhost:8000',
      '/accounts': 'http://localhost:8000',
      '/balances': 'http://localhost:8000',
      '/account': 'http://localhost:8000',
      '/regulatory-capital': 'http://localhost:8000',
      '/assets': 'http://localhost:8000',
      '/liabilities': 'http://localhost:8000',
      '/liquidity': 'http://localhost:8000',
      '/large-risks': 'http://localhost:8000',
      '/loans': 'http://localhost:8000',
      '/deposits': 'http://localhost:8000',
      '/loan-profit': 'http://localhost:8000',
      '/apply-loan-interest': 'http://localhost:8000',
      '/deposit-cost': 'http://localhost:8000',
      '/apply-deposit-interest': 'http://localhost:8000',
      '/convert-currency': 'http://localhost:8000',
      '/financial-summary-in-currency': 'http://localhost:8000',
    }
  }
})