import { useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { Navbar } from './components/Navbar';
import { HeroSection } from './components/HeroSection';
import { WorkspaceLayout } from './components/WorkspaceLayout';
import { AuthPage } from './components/AuthPage';
import { ChatScreen } from './components/ChatScreen';
import { SignupComplete } from './components/SignupComplete';
import { TutorialGuide } from './components/TutorialGuide';
import { TravelDashboard } from './components/TravelDashboard';

// 화면 단계를 정의합니다
type PageState = 'home' | 'auth' | 'chat' | 'complete' | 'workspace' | 'tutorial' | 'dashboard';

export default function App() {
  // 상태를 boolean이 아니라 문자열로 관리
  const [pageState, setPageState] = useState<PageState>('home');
  const [userName, setUserName] = useState('');
  const [showTutorial, setShowTutorial] = useState(true);

  // 1. 로그인 버튼 클릭 시 -> 인증 페이지(로그인)로
  const handleLoginClick = () => {
    setPageState('auth');
  };

  // 2. 회원가입 버튼 클릭 시 -> 인증 페이지(회원가입)로
  const handleSignupClick = () => {
    setPageState('auth');
  };

  // 3. 로그인 성공 시 -> 튜토리얼 가이드로
  const handleLoginSuccess = () => {
    setPageState('tutorial');
  };

  // 8. 튜토리얼 닫기 -> 대시보드로
  const handleCloseTutorial = () => {
    setShowTutorial(false);
    setPageState('dashboard');
  };

  // 4. 회원가입 성공 시 -> 채팅 화면으로
  const handleSignupSuccess = (name: string) => {
    setUserName(name);
    setPageState('chat');
  };

  // 5. 채팅 완료 시 -> 완료 화면으로
  const handleChatComplete = () => {
    setPageState('complete');
  };

  // 6. 뒤로가기 -> 홈으로
  const handleBackToHome = () => {
    setPageState('home');
  };

  // 7. 로그인 페이지로
  const handleGoToLogin = () => {
    setPageState('auth');
  };

  // 9. 대시보드로 이동
  const handleGoToDashboard = () => {
    setPageState('dashboard');
  };

  return (
    <div className="app-container-wrapper">
      <div className="app-container">
        <AnimatePresence mode="wait">

          {/* 홈 화면 */}
          {pageState === 'home' && (
            <motion.div
              key="home-layout"
              exit={{ opacity: 0, scale: 1.05 }}
              transition={{ duration: 0.5 }}
              className="w-full"
              style={{ position: 'relative' }}
            >
              <Navbar />
              <HeroSection onLogin={handleLoginClick} onSignup={handleSignupClick} />
            </motion.div>
          )}

          {/* 인증 페이지 (로그인/회원가입) */}
          {pageState === 'auth' && (
            <motion.div
              key="auth"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              style={{ width: '100%', height: '100%' }}
            >
              <AuthPage
                onBack={handleBackToHome}
                onLoginSuccess={handleLoginSuccess}
                onSignupSuccess={handleSignupSuccess}
              />
            </motion.div>
          )}

          {/* 채팅 화면 (회원가입 후) */}
          {pageState === 'chat' && (
            <motion.div
              key="chat"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5 }}
              style={{ width: '100%', height: '100%' }}
            >
              <ChatScreen userName={userName} onComplete={handleChatComplete} />
            </motion.div>
          )}

          {/* 회원가입 완료 화면 */}
          {pageState === 'complete' && (
            <motion.div
              key="complete"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.5 }}
              style={{ width: '100%', height: '100%' }}
            >
              <SignupComplete
                userName={userName}
                onGoHome={handleBackToHome}
                onGoLogin={handleGoToLogin}
              />
            </motion.div>
          )}

          {/* 튜토리얼 가이드 */}
          {pageState === 'tutorial' && showTutorial && (
            <TutorialGuide onClose={handleCloseTutorial} />
          )}

          {/* 여행 대시보드 */}
          {pageState === 'dashboard' && (
            <motion.div
              key="dashboard"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5 }}
              style={{ width: '100%', height: '100%' }}
            >
              <TravelDashboard onLogoClick={handleGoToDashboard} />
            </motion.div>
          )}

          {/* 워크스페이스 (다이어리) */}
          {pageState === 'workspace' && (
            <motion.div
              key="workspace"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 1, ease: "easeOut" }}
              className="h-full"
            >
              <WorkspaceLayout />
            </motion.div>
          )}

        </AnimatePresence>
      </div>
    </div>
  );
}