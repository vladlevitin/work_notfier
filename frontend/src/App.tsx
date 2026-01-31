import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { PostsPage } from './pages/Posts';
import { PostDetailPage } from './pages/PostDetail';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<PostsPage />} />
        <Route path="/post/:postId" element={<PostDetailPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
