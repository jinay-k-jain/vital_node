import React, { useEffect } from 'react';
import { useAppStore } from './store/appStore';
import { LoginScreen } from './screens/LoginScreen';
import { DashboardScreen } from './screens/DashboardScreen';
import { PatientQueueScreen } from './screens/PatientQueueScreen';
import { NewAssessmentScreen } from './screens/NewAssessmentScreen';
import { AIResultScreen } from './screens/AIResultScreen';
import { PatientDetailScreen } from './screens/PatientDetailScreen';
import { ReassessmentScreen } from './screens/ReassessmentScreen';
import { AuditLogScreen } from './screens/AuditLogScreen';
import { SurgeModeScreen } from './screens/SurgeModeScreen';
import { AnalyticsScreen } from './screens/AnalyticsScreen';
import { SystemInfoScreen } from './screens/SystemInfoScreen';
import { SettingsScreen } from './screens/SettingsScreen';
import { Sidebar } from './components/layout/Sidebar';
import { TopBar } from './components/layout/TopBar';
import { connectQueueSocket, disconnectQueueSocket, setQueueUpdateHandler } from './lib/websocket';
import { mapPatient } from './lib/api';

function AppShell({ children }: { children: React.ReactNode }) {
  const setPatients = useAppStore(s => s.fetchQueue);

  useEffect(() => {
    // Wire WebSocket queue updates — merge into existing patients, preserve aiRecommendation
    setQueueUpdateHandler((queue: any[]) => {
      const mapped = queue.map(mapPatient);
      useAppStore.setState(state => {
        const existingMap = new Map(state.patients.map(p => [p.id, p]));
        const incomingMap = new Map(mapped.map(p => [p.id, p]));
        const updated = state.patients.map(existing => {
          const fresh = incomingMap.get(existing.id);
          if (!fresh) return existing;
          return {
            ...fresh,
            aiRecommendation: fresh.aiRecommendation || existing.aiRecommendation,
            nurseDecision: fresh.nurseDecision || existing.nurseDecision,
            _assessmentId: (fresh as any)._assessmentId || (existing as any)._assessmentId,
          };
        });
        const newOnes = mapped.filter(p => !existingMap.has(p.id));
        return { patients: [...updated, ...newOnes] };
      });
    });
    connectQueueSocket();
    return () => disconnectQueueSocket();
  }, []);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-y-auto scrollbar-thin">
          {children}
        </main>
      </div>
    </div>
  );
}

function AppContent() {
  const currentView = useAppStore(s => s.currentView);
  const screens: Record<string, React.ReactNode> = {
    dashboard: <DashboardScreen />,
    queue: <PatientQueueScreen />,
    'new-assessment': <NewAssessmentScreen />,
    'ai-result': <AIResultScreen />,
    'patient-detail': <PatientDetailScreen />,
    reassessment: <ReassessmentScreen />,
    audit: <AuditLogScreen />,
    surge: <SurgeModeScreen />,
    analytics: <AnalyticsScreen />,
    system: <SystemInfoScreen />,
    settings: <SettingsScreen />,
  };
  return <>{screens[currentView] || <DashboardScreen />}</>;
}

export default function App() {
  const isAuthenticated = useAppStore(s => s.isAuthenticated);
  if (!isAuthenticated) return <LoginScreen />;
  return <AppShell><AppContent /></AppShell>;
}
