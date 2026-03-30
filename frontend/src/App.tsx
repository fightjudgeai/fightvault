import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Promotions from './pages/Promotions'
import PromotionDetail from './pages/PromotionDetail'
import Fighters from './pages/Fighters'
import FighterProfile from './pages/FighterProfile'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/promotions" replace />} />
          <Route path="promotions" element={<Promotions />} />
          <Route path="promotions/:id" element={<PromotionDetail />} />
          <Route path="fighters" element={<Fighters />} />
          <Route path="fighters/:id" element={<FighterProfile />} />
          <Route path="*" element={<Navigate to="/promotions" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
