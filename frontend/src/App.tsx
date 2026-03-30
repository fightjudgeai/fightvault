import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Fighters from './pages/Fighters'
import FighterProfile from './pages/FighterProfile'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Fighters />} />
          <Route path="fighters" element={<Fighters />} />
          <Route path="fighters/:id" element={<FighterProfile />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
