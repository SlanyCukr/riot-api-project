import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Home } from "./pages/Home";
import { SmurfDetectionPage } from "./pages/SmurfDetectionPage";

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/smurf-detection" element={<SmurfDetectionPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
