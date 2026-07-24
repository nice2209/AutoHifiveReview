import React, { useState, useEffect } from 'react'
import {
  Settings,
  BookOpen,
  Clock,
  Play,
  FileText,
  CheckCircle2,
  XCircle,
  RefreshCw,
  AlertCircle,
  Edit3,
  Trash2,
  ShieldAlert,
  Award,
  User,
  Calendar,
  Plus,
  ListPlus,
  Wand2,
  Save,
  Check
} from 'lucide-react'

// Base URL for API (empty for local proxy, falls back to local server if hosted on GitHub Pages)
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' ? '' : 'http://localhost:5000'

function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [loading, setLoading] = useState(false)
  const [hifiveLoading, setHifiveLoading] = useState(false)
  const [logsLoading, setLogsLoading] = useState(false)
  const [runningDiary, setRunningDiary] = useState(false)
  
  // Data States
  const [config, setConfig] = useState({
    base_url: 'https://www.hifive.go.kr',
    lms_url: '/mobile/mInvovedReportingMain.do',
    api: {},
    schedule: { run_time: '18:00', timezone: 'Asia/Seoul' }
  })
  
  const [credentials, setCredentials] = useState({
    user_id: '',
    password: '',
    password_masked: ''
  })
  
  const [words, setWords] = useState({
    adjectives: [],
    nouns: [],
    patterns: [],
    departments: []
  })
  
  const [logs, setLogs] = useState('')
  const [hifiveData, setHifiveData] = useState(null)
  
  // Custom Sentence Test
  const [testSentences, setTestSentences] = useState([])
  
  // UI State for Editing/Adding
  const [editingWeek, setEditingWeek] = useState(null)
  const [editForm, setEditForm] = useState({
    week_num: 1,
    trainee_seq: '',
    entries: []
  })
  
  // Notification Banner
  const [notification, setNotification] = useState(null)

  const showNotification = (message, type = 'info') => {
    setNotification({ message, type })
    setTimeout(() => setNotification(null), 5000)
  }

  // Load Initial Configuration Data
  const loadInitialData = async () => {
    setLoading(true)
    try {
      const [configRes, credsRes, wordsRes] = await Promise.all([
        fetch(`${API_BASE}/api/config`),
        fetch(`${API_BASE}/api/credentials`),
        fetch(`${API_BASE}/api/words`)
      ])
      
      if (configRes.ok) setConfig(await configRes.json())
      if (credsRes.ok) setCredentials(await credsRes.json())
      if (wordsRes.ok) setWords(await wordsRes.json())
      
      // Auto fetch HIFIVE status if credentials look populated
      fetchHifiveStatus(false)
    } catch (err) {
      console.error('Failed to load local config', err)
      showNotification('로컬 설정 데이터를 불러오는데 실패했습니다.', 'danger')
    } finally {
      setLoading(false)
    }
  }

  const fetchHifiveStatus = async (silent = true) => {
    if (!silent) setHifiveLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/hifive/fetch`, { method: 'POST' })
      const data = await res.json()
      if (data.success) {
        setHifiveData(data)
        if (!silent) showNotification('HIFIVE 서버 데이터 연동 성공!', 'success')
      } else {
        if (!silent) showNotification(data.error || 'HIFIVE 데이터 로드 실패', 'danger')
      }
    } catch (err) {
      console.error(err)
      if (!silent) showNotification('HIFIVE 연동 중 오류가 발생했습니다.', 'danger')
    } finally {
      setHifiveLoading(false)
    }
  }

  const fetchLogs = async () => {
    setLogsLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/logs`)
      const data = await res.json()
      setLogs(data.logs)
    } catch (err) {
      showNotification('로그 조회 실패', 'danger')
    } finally {
      setLogsLoading(false)
    }
  }

  const testGenerateSentences = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sentence-test`)
      const data = await res.json()
      setTestSentences(data.sentences || [])
    } catch (err) {
      showNotification('랜덤 문장 생성 실패', 'danger')
    }
  }

  useEffect(() => {
    loadInitialData()
    fetchLogs()
  }, [])

  // Action: Save Config
  const saveConfig = async (e) => {
    e.preventDefault()
    try {
      const res = await fetch(`${API_BASE}/api/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      })
      if (res.ok) {
        showNotification('시스템 설정 저장 완료!', 'success')
      } else {
        showNotification('설정 저장 중 오류가 발생했습니다.', 'danger')
      }
    } catch (err) {
      showNotification('설정 저장 실패', 'danger')
    }
  }

  // Action: Save Credentials
  const saveCredentials = async (e) => {
    e.preventDefault()
    try {
      const res = await fetch(`${API_BASE}/api/credentials`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: credentials.user_id,
          password: credentials.password
        })
      })
      if (res.ok) {
        showNotification('인증 정보 저장 완료! HIFIVE 연동을 재시도합니다.', 'success')
        fetchHifiveStatus(false)
      } else {
        showNotification('인증 정보 저장 중 오류가 발생했습니다.', 'danger')
      }
    } catch (err) {
      showNotification('인증 정보 저장 실패', 'danger')
    }
  }

  // Action: Save Words
  const saveWords = async (newWords) => {
    const updated = newWords || words
    try {
      const res = await fetch(`${API_BASE}/api/words`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated)
      })
      if (res.ok) {
        setWords(updated)
        showNotification('랜덤 단어 사전 저장 완료!', 'success')
      } else {
        showNotification('단어 저장 실패', 'danger')
      }
    } catch (err) {
      showNotification('단어 저장 오류', 'danger')
    }
  }

  // Action: Run Script
  const triggerAutoDiary = async (dryRun = false) => {
    setRunningDiary(true)
    showNotification(dryRun ? '일지 작성 테스트(Dry-Run) 시작...' : '실습일지 자동 작성 제출 시작...', 'info')
    try {
      const res = await fetch(`${API_BASE}/api/run-diary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dry_run: dryRun })
      })
      const data = await res.json()
      if (data.success) {
        showNotification(dryRun ? 'Dry-run 완료! 로그를 확인해 주세요.' : '자동 실습일지 제출 완료!', 'success')
        fetchLogs()
        fetchHifiveStatus(true)
      } else {
        showNotification(`실행 중 오류: ${data.error || '알 수 없는 오류'}`, 'danger')
      }
    } catch (err) {
      showNotification('스크립트 실행 중 서버 오류', 'danger')
    } finally {
      setRunningDiary(false)
    }
  }

  // Action: Update Personal Info Agreement
  const savePersonalInfoAgree = async (yn1, yn2) => {
    try {
      const res = await fetch(`${API_BASE}/api/hifive/agree`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agree_yn1: yn1, agree_yn2: yn2 })
      })
      const data = await res.json()
      if (data.success) {
        showNotification('개인정보 이용/제공 동의 저장 완료!', 'success')
        fetchHifiveStatus(true)
      } else {
        showNotification(`동의 저장 실패: ${data.error}`, 'danger')
      }
    } catch (err) {
      showNotification('동의 처리 실패', 'danger')
    }
  }

  // Action: Open Editor for Adding/Editing manual week
  const openManualWrite = (weekNum) => {
    if (!hifiveData || !hifiveData.trainee_info) {
      showNotification('HIFIVE 실습생 정보가 없습니다. 먼저 데이터 연동을 해주세요.', 'warning')
      return
    }

    const traineeSeq = hifiveData.trainee_info.TRAINEE_SEQ
    const startDateStr = hifiveData.trainee_info.TRAINEE_START_DATE
    const startDate = new Date(
      parseInt(startDateStr.slice(0, 4)),
      parseInt(startDateStr.slice(4, 6)) - 1,
      parseInt(startDateStr.slice(6, 8))
    )

    // Calculate dates for the requested week
    // Monday of the week is startDate + (weekNum - 1)*7
    const mondayOfTargetWeek = new Date(startDate.getTime())
    mondayOfTargetWeek.setDate(startDate.getDate() + (weekNum - 1) * 7)

    const dayNames = ['월', '화', '수', '목', '금', '토', '일']
    const existingForWeek = hifiveData.existing_entries.filter(
      (e) => e.REPORT_WEEK === String(weekNum)
    )

    const newEntries = []
    for (let i = 0; i < 7; i++) {
      const currentDate = new Date(mondayOfTargetWeek.getTime())
      currentDate.setDate(mondayOfTargetWeek.getDate() + i)
      
      const formattedDateStr = currentDate.toISOString().slice(0, 10).replace(/-/g, '')
      const dayName = dayNames[i]

      const matchedExisting = existingForWeek.find((e) => e.DY === dayName)
      
      let workFlag = 'Y'
      let content = ''
      let startTime = '09:00'
      let endTime = '18:00'
      let department = words.departments[0] || '개발팀'

      if (i >= 5) {
        workFlag = 'N'
        startTime = ''
        endTime = ''
        department = ''
      }

      if (matchedExisting) {
        workFlag = matchedExisting.WORK_FLAG
        // Decode reportDesc if possible
        if (matchedExisting.REPORT_DESC) {
          content = matchedExisting.REPORT_DESC
        }
      }

      newEntries.push({
        date: currentDate,
        dateStr: formattedDateStr,
        day_name: dayName,
        content: content,
        work_flag: workFlag,
        start_time: startTime,
        end_time: endTime,
        department: department
      })
    }

    setEditForm({
      week_num: weekNum,
      trainee_seq: traineeSeq,
      entries: newEntries
    })
    setEditingWeek(weekNum)
  }

  // Helper: auto generate random sentence for a specific day in manual editor
  const generateRandomSentenceForDay = (idx) => {
    if (words.nouns.length === 0 || words.adjectives.length === 0 || words.patterns.length === 0) {
      showNotification('단어 사전 정보가 비어있습니다.', 'warning')
      return
    }

    const selectRandom = (arr) => arr[Math.floor(Math.random() * arr.length)]
    const noun = selectRandom(words.nouns)
    const adj = selectRandom(words.adjectives)
    const pattern = selectRandom(words.patterns)
    const department = selectRandom(words.departments) || '개발팀'

    // Get subject particle
    const lastChar = noun[noun.length - 1]
    const code = lastChar.charCodeAt(0) - 0xAC00
    let p = '을'
    let sp = '이'
    if (code >= 0 && code < 11172) {
      p = code % 28 === 0 ? '를' : '을'
      sp = code % 28 === 0 ? '가' : '이'
    } else if (/^[a-zA-Z0-9]$/.test(lastChar)) {
      p = '을'
      sp = '이'
    } else {
      p = '를'
      sp = '가'
    }

    const sentence = pattern
      .replace('{adj}', adj)
      .replace('{noun}', noun)
      .replace('{p}', p)
      .replace('{sp}', sp)

    const updatedEntries = [...editForm.entries]
    updatedEntries[idx] = {
      ...updatedEntries[idx],
      content: sentence,
      department: department,
      work_flag: 'Y'
    }
    setEditForm({ ...editForm, entries: updatedEntries })
  }

  const handleManualSave = async () => {
    // Check if at least one entry has content
    const valid = editForm.entries.some(e => e.work_flag === 'Y' && e.content.trim() !== '')
    if (!valid) {
      showNotification('적어도 하루 이상의 실습 기록과 내용이 입력되어야 합니다.', 'warning')
      return
    }

    setHifiveLoading(true)
    try {
      // Serialize entries
      const serializedEntries = editForm.entries.map((e) => ({
        day_name: e.day_name,
        content: e.content,
        work_flag: e.work_flag,
        start_time: e.start_time,
        end_time: e.end_time,
        department: e.department
      }))

      const res = await fetch(`${API_BASE}/api/hifive/save-manual`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          trainee_seq: editForm.trainee_seq,
          week_num: editForm.week_num,
          entries: serializedEntries
        })
      })

      const data = await res.json()
      if (data.success) {
        showNotification(`${editForm.week_num}주차 실습일지 수동 저장 성공!`, 'success')
        setEditingWeek(null)
        fetchHifiveStatus(true)
      } else {
        showNotification(`저장 실패: ${data.error}`, 'danger')
      }
    } catch (err) {
      showNotification('수동 일지 저장 중 서버 오류', 'danger')
    } finally {
      setHifiveLoading(false)
    }
  }

  const handleManualDelete = async (weekNum) => {
    if (!window.confirm(`${weekNum}주차 일지를 정말로 삭제하시겠습니까?`)) return
    
    setHifiveLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/hifive/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          trainee_seq: hifiveData.trainee_info.TRAINEE_SEQ,
          week_num: weekNum
        })
      })
      const data = await res.json()
      if (data.success) {
        showNotification(`${weekNum}주차 실습일지 삭제 성공!`, 'success')
        fetchHifiveStatus(true)
      } else {
        showNotification(`삭제 실패: ${data.error}`, 'danger')
      }
    } catch (err) {
      showNotification('일지 삭제 실패', 'danger')
    } finally {
      setHifiveLoading(false)
    }
  }

  // Tag helper
  const addWordTag = (category, value) => {
    if (!value.trim()) return
    if (words[category].includes(value.trim())) return
    const updated = {
      ...words,
      [category]: [...words[category], value.trim()]
    }
    saveWords(updated)
  }

  const removeWordTag = (category, idx) => {
    const list = [...words[category]]
    list.splice(idx, 1)
    const updated = { ...words, [category]: list }
    saveWords(updated)
  }

  // Calculate current week helper
  const getCurrentWeek = () => {
    if (!hifiveData || !hifiveData.trainee_info) return 0
    const startStr = hifiveData.trainee_info.TRAINEE_START_DATE
    const start = new Date(
      parseInt(startStr.slice(0, 4)),
      parseInt(startStr.slice(4, 6)) - 1,
      parseInt(startStr.slice(6, 8))
    )
    const diff = new Date().getTime() - start.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    return Math.max(1, Math.floor(days / 7) + 1)
  }

  const currentCalculatedWeek = getCurrentWeek()

  return (
    <div className="animated-in">
      {/* Header */}
      <header className="app-header">
        <div className="container header-content">
          <a href="#" className="brand">
            <div className="brand-icon">
              <Award size={18} color="#fff" />
            </div>
            <span>HIFIVE <span className="gradient-text">Sync-LMS</span></span>
          </a>
          
          <div className="tabs">
            <button 
              className={`tab-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
              onClick={() => setActiveTab('dashboard')}
            >
              <BookOpen size={16} /> 대시보드
            </button>
            <button 
              className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`}
              onClick={() => setActiveTab('history')}
            >
              <FileText size={16} /> 일지 관리
            </button>
            <button 
              className={`tab-btn ${activeTab === 'words' ? 'active' : ''}`}
              onClick={() => setActiveTab('words')}
            >
              <Wand2 size={16} /> 랜덤 단어 사전
            </button>
            <button 
              className={`tab-btn ${activeTab === 'settings' ? 'active' : ''}`}
              onClick={() => setActiveTab('settings')}
            >
              <Settings size={16} /> 시스템 설정
            </button>
            <button 
              className={`tab-btn ${activeTab === 'logs' ? 'active' : ''}`}
              onClick={() => setActiveTab('logs')}
            >
              <Clock size={16} /> 실행 로그
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="container" style={{ padding: '32px 0 60px' }}>
        
        {/* Banner notifications */}
        {notification && (
          <div 
            className={`badge badge-${notification.type} animated-in`} 
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '10px', 
              padding: '16px 24px', 
              borderRadius: '12px',
              width: '100%',
              fontSize: '0.95rem',
              marginBottom: '24px',
              textTransform: 'none',
              boxShadow: 'var(--shadow-md)'
            }}
          >
            <AlertCircle size={20} />
            <span>{notification.message}</span>
          </div>
        )}

        {/* LOADING STATE */}
        {loading && (
          <div style={{ textAlign: 'center', padding: '100px 0' }}>
            <RefreshCw size={48} className="pulse-glow" style={{ color: 'var(--accent-primary)' }} />
            <p style={{ marginTop: '16px', color: 'var(--text-secondary)' }}>로컬 데이터 동기화 중...</p>
          </div>
        )}

        {!loading && (
          <>
            {/* 1. DASHBOARD TAB */}
            {activeTab === 'dashboard' && (
              <div className="grid animated-in" style={{ gridTemplateColumns: '2fr 1fr' }}>
                <div className="grid" style={{ gap: '24px' }}>
                  {/* Trainee Card */}
                  <div className="card">
                    <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '1.25rem', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '12px' }}>
                      <User size={20} className="gradient-text" /> 
                      현장실습 LMS 연동 정보
                      {hifiveLoading && <RefreshCw size={14} className="pulse-glow" style={{ marginLeft: 'auto' }} />}
                      {!hifiveLoading && (
                        <button 
                          onClick={() => fetchHifiveStatus(false)} 
                          className="btn btn-secondary" 
                          style={{ padding: '4px 10px', fontSize: '0.75rem', borderRadius: '4px', marginLeft: 'auto' }}
                        >
                          새로고침
                        </button>
                      )}
                    </h3>

                    {hifiveData && hifiveData.trainee_info ? (
                      <div className="grid grid-cols-2" style={{ gap: '20px', textAlign: 'left', marginTop: '20px' }}>
                        <div>
                          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>실습기관명</p>
                          <p style={{ fontSize: '1.1rem', fontWeight: '600' }}>{hifiveData.trainee_info.EMPLOY_NM}</p>
                        </div>
                        <div>
                          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>전공학과</p>
                          <p style={{ fontSize: '1.1rem', fontWeight: '600' }}>{hifiveData.trainee_info.TRAINEE_MAJOR_NM}</p>
                        </div>
                        <div>
                          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>실습 시작일</p>
                          <p style={{ fontSize: '1rem', fontWeight: '500', fontFamily: 'var(--font-mono)' }}>
                            {hifiveData.trainee_info.TRAINEE_START_DATE.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')}
                          </p>
                        </div>
                        <div>
                          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>실습 종료일</p>
                          <p style={{ fontSize: '1rem', fontWeight: '500', fontFamily: 'var(--font-mono)' }}>
                            {hifiveData.trainee_info.TRAINEE_END_DATE.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')}
                          </p>
                        </div>
                        <div style={{ gridColumn: 'span 2', background: 'rgba(255,255,255,0.02)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.04)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>진행 상태</p>
                              <p style={{ fontSize: '1.2rem', fontWeight: '700' }}>
                                총 {currentCalculatedWeek}주차 중 <span className="gradient-text">{hifiveData.trainee_info.LAST_WRITE_REPORT_WEEK}주차</span> 작성됨
                              </p>
                            </div>
                            <span className={`badge ${currentCalculatedWeek <= parseInt(hifiveData.trainee_info.LAST_WRITE_REPORT_WEEK) ? 'badge-success' : 'badge-warning'}`}>
                              {currentCalculatedWeek <= parseInt(hifiveData.trainee_info.LAST_WRITE_REPORT_WEEK) ? '최신화 완료' : '미작성 일지 있음'}
                            </span>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div style={{ padding: '40px 0', color: 'var(--text-secondary)', textAlign: 'center' }}>
                        <ShieldAlert size={40} style={{ color: 'rgba(245, 158, 11, 0.7)', marginBottom: '12px' }} />
                        <p>HIFIVE 로그인 연동이 필요합니다.</p>
                        <p style={{ fontSize: '0.85rem' }}>[시스템 설정] 탭에서 ID/PW를 입력하고 로그인해 주세요.</p>
                        <button className="btn btn-primary" style={{ marginTop: '16px' }} onClick={() => setActiveTab('settings')}>
                          로그인 하러가기
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Quick Controls Card */}
                  <div className="card">
                    <h3 style={{ fontSize: '1.25rem', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '12px' }}>
                      실습일지 자동화 수동 조작
                    </h3>
                    <div style={{ display: 'flex', gap: '16px', marginTop: '20px' }}>
                      <div style={{ flex: 1, padding: '16px', borderRadius: '12px', border: '1px solid var(--border-color)', background: 'rgba(255,255,255,0.01)', textAlign: 'left' }}>
                        <h4 style={{ fontSize: '1rem', color: 'var(--accent-primary)', marginBottom: '8px' }}>자동 작성 테스트 (Dry-Run)</h4>
                        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                          HIFIVE 서버에 실제로 저장하지 않고, 랜덤으로 생성된 문장과 오늘 자 작성 대상인지 결과를 로그에만 남깁니다.
                        </p>
                        <button 
                          className="btn btn-secondary btn-glow" 
                          disabled={runningDiary}
                          onClick={() => triggerAutoDiary(true)}
                          style={{ width: '100%' }}
                        >
                          {runningDiary ? <RefreshCw className="pulse-glow" size={16} /> : <Play size={16} />}
                          테스트 실행 (Dry Run)
                        </button>
                      </div>

                      <div style={{ flex: 1, padding: '16px', borderRadius: '12px', border: '1px solid rgba(168,85,247,0.3)', background: 'rgba(168,85,247,0.02)', textAlign: 'left' }}>
                        <h4 style={{ fontSize: '1rem', color: 'var(--accent-secondary)', marginBottom: '8px' }}>실제 실습일지 자동 제출</h4>
                        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                          오늘 날짜 기준으로 미작성된 실습일지가 있으면 랜덤 문장으로 일지를 구성하여 즉시 HIFIVE 서버로 제출합니다.
                        </p>
                        <button 
                          className="btn btn-primary btn-glow" 
                          disabled={runningDiary}
                          onClick={() => triggerAutoDiary(false)}
                          style={{ width: '100%' }}
                        >
                          {runningDiary ? <RefreshCw className="pulse-glow" size={16} /> : <CheckCircle2 size={16} />}
                          자동 제출 실행
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Right Column: Status Summary */}
                <div className="grid" style={{ gap: '24px', alignContent: 'start' }}>
                  {/* Personal Data Consent */}
                  <div className="card">
                    <h3 style={{ fontSize: '1.1rem', marginBottom: '16px' }}>개인정보 제공 동의</h3>
                    {hifiveData && hifiveData.agree_status ? (
                      <div style={{ textAlign: 'left', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: '0.9rem' }}>수집·이용 동의 (필수)</span>
                          <span className={`badge ${hifiveData.agree_status.PERSONAL_INFO_AGREE_YN1 === 'Y' ? 'badge-success' : 'badge-danger'}`}>
                            {hifiveData.agree_status.PERSONAL_INFO_AGREE_YN1 === 'Y' ? '동의완료' : '미동의'}
                          </span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: '0.9rem' }}>제3자 제공 동의 (선택)</span>
                          <span className={`badge ${hifiveData.agree_status.PERSONAL_INFO_AGREE_YN2 === 'Y' ? 'badge-success' : 'badge-danger'}`}>
                            {hifiveData.agree_status.PERSONAL_INFO_AGREE_YN2 === 'Y' ? '동의완료' : '미동의'}
                          </span>
                        </div>
                        
                        {(hifiveData.agree_status.PERSONAL_INFO_AGREE_YN1 !== 'Y' || hifiveData.agree_status.PERSONAL_INFO_AGREE_YN2 !== 'Y') && (
                          <button 
                            className="btn btn-primary" 
                            style={{ width: '100%', fontSize: '0.8rem', padding: '8px 12px', marginTop: '10px' }}
                            onClick={() => savePersonalInfoAgree('Y', 'Y')}
                          >
                            모두 즉시 일괄동의
                          </button>
                        )}
                      </div>
                    ) : (
                      <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>동의 조회 대기 중</p>
                    )}
                  </div>

                  {/* Sentence tester preview */}
                  <div className="card" style={{ padding: '20px' }}>
                    <h3 style={{ fontSize: '1.1rem', marginBottom: '12px', display: 'flex', justifyItems: 'center', gap: '8px' }}>
                      <Wand2 size={16} className="gradient-text" /> 랜덤 문장 테스트
                    </h3>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                      현재 등록된 단어 사전 기반으로 생성되는 예시 실습 일지 문장입니다.
                    </p>
                    <button className="btn btn-secondary" style={{ width: '100%', padding: '6px', fontSize: '0.8rem', marginBottom: '12px' }} onClick={testGenerateSentences}>
                      랜덤 문장 5개 생성하기
                    </button>
                    {testSentences.length > 0 && (
                      <ul style={{ paddingLeft: '16px', margin: 0, textAlign: 'left', fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {testSentences.map((s, idx) => (
                          <li key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '4px' }}>{s}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* 2. HISTORY / MANUAL EDIT TAB */}
            {activeTab === 'history' && (
              <div className="animated-in">
                {editingWeek ? (
                  /* Manual Editor Mode */
                  <div className="card" style={{ textAlign: 'left' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '16px', marginBottom: '20px' }}>
                      <h2 style={{ margin: 0 }}>
                        <span className="gradient-text">{editForm.week_num}주차</span> 실습일지 상세 수정/작성
                      </h2>
                      <div style={{ display: 'flex', gap: '12px' }}>
                        <button className="btn btn-secondary" onClick={() => setEditingWeek(null)}>취소</button>
                        <button className="btn btn-primary" onClick={handleManualSave}>
                          <Save size={16} /> HIFIVE 서버 저장
                        </button>
                      </div>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                      {editForm.entries.map((entry, idx) => (
                        <div 
                          key={idx} 
                          style={{ 
                            padding: '16px', 
                            borderRadius: '12px', 
                            background: entry.work_flag === 'Y' ? 'rgba(255,255,255,0.02)' : 'rgba(239, 68, 68, 0.02)',
                            border: entry.work_flag === 'Y' ? '1px solid var(--border-color)' : '1px solid rgba(239, 68, 68, 0.15)',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '12px'
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <span 
                              className={`badge ${
                                ['토','일'].includes(entry.day_name) 
                                  ? 'badge-danger' 
                                  : entry.work_flag === 'Y' ? 'badge-info' : 'badge-warning'
                              }`}
                              style={{ width: '50px', justifyContent: 'center' }}
                            >
                              {entry.day_name}요일
                            </span>
                            <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                              {entry.dateStr.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')}
                            </span>
                            
                            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', marginLeft: 'auto', fontSize: '0.85rem' }}>
                              <input 
                                type="checkbox" 
                                checked={entry.work_flag === 'Y'} 
                                onChange={(e) => {
                                  const updated = [...editForm.entries]
                                  updated[idx] = {
                                    ...updated[idx],
                                    work_flag: e.target.checked ? 'Y' : 'N',
                                    start_time: e.target.checked ? '09:00' : '',
                                    end_time: e.target.checked ? '18:00' : '',
                                    department: e.target.checked ? (words.departments[0] || '개발팀') : '',
                                    content: e.target.checked ? updated[idx].content : ''
                                  }
                                  setEditForm({ ...editForm, entries: updated })
                                }}
                              />
                              실습 진행 여부 (Y/N)
                            </label>
                          </div>

                          {entry.work_flag === 'Y' && (
                            <div className="grid grid-cols-3" style={{ gap: '12px' }}>
                              <div className="form-group" style={{ marginBottom: 0 }}>
                                <span className="form-label">부서</span>
                                <input 
                                  type="text" 
                                  className="form-input" 
                                  value={entry.department}
                                  placeholder="예: 개발팀"
                                  onChange={(e) => {
                                    const updated = [...editForm.entries]
                                    updated[idx].department = e.target.value
                                    setEditForm({ ...editForm, entries: updated })
                                  }}
                                />
                              </div>
                              <div className="form-group" style={{ marginBottom: 0 }}>
                                <span className="form-label">시작 시간</span>
                                <input 
                                  type="text" 
                                  className="form-input" 
                                  value={entry.start_time}
                                  placeholder="09:00"
                                  onChange={(e) => {
                                    const updated = [...editForm.entries]
                                    updated[idx].start_time = e.target.value
                                    setEditForm({ ...editForm, entries: updated })
                                  }}
                                />
                              </div>
                              <div className="form-group" style={{ marginBottom: 0 }}>
                                <span className="form-label">종료 시간</span>
                                <input 
                                  type="text" 
                                  className="form-input" 
                                  value={entry.end_time}
                                  placeholder="18:00"
                                  onChange={(e) => {
                                    const updated = [...editForm.entries]
                                    updated[idx].end_time = e.target.value
                                    setEditForm({ ...editForm, entries: updated })
                                  }}
                                />
                              </div>

                              <div className="form-group" style={{ gridColumn: 'span 3', marginBottom: 0 }}>
                                <span className="form-label" style={{ display: 'flex', justifyContent: 'space-between' }}>
                                  실습 일지 상세 내용
                                  <button 
                                    className="btn btn-secondary" 
                                    style={{ padding: '2px 8px', fontSize: '0.75rem', borderRadius: '4px' }}
                                    onClick={() => generateRandomSentenceForDay(idx)}
                                  >
                                    <Wand2 size={12} /> AI 랜덤 문장 생성
                                  </button>
                                </span>
                                <textarea 
                                  className="form-input" 
                                  rows={2}
                                  value={entry.content}
                                  placeholder="실습 내용을 입력하거나 AI 문장 생성 버튼을 눌러주세요."
                                  onChange={(e) => {
                                    const updated = [...editForm.entries]
                                    updated[idx].content = e.target.value
                                    setEditForm({ ...editForm, entries: updated })
                                  }}
                                  style={{ resize: 'vertical' }}
                                />
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '20px' }}>
                      <button className="btn btn-secondary" onClick={() => setEditingWeek(null)}>취소</button>
                      <button className="btn btn-primary" onClick={handleManualSave}>
                        <Save size={16} /> HIFIVE 서버 저장
                      </button>
                    </div>
                  </div>
                ) : (
                  /* History Weeks List Mode */
                  <div className="card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '16px', marginBottom: '20px' }}>
                      <h3 style={{ margin: 0, fontSize: '1.25rem' }}>주차별 실습일지 관리 목록</h3>
                      <button 
                        className="btn btn-primary" 
                        onClick={() => {
                          const nextWeek = hifiveData ? parseInt(hifiveData.trainee_info.LAST_WRITE_REPORT_WEEK) + 1 : 1
                          openManualWrite(nextWeek)
                        }}
                      >
                        <Plus size={16} /> 신규 주차 일지 추가
                      </button>
                    </div>

                    {hifiveData && hifiveData.existing_entries ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        {/* Group entries by week */}
                        {Array.from(new Set(hifiveData.existing_entries.map(e => parseInt(e.REPORT_WEEK)))).sort((a, b) => b - a).map((weekNum) => {
                          const weekEntries = hifiveData.existing_entries.filter(e => parseInt(e.REPORT_WEEK) === weekNum)
                          // Summary description from weekly summary (TERM_CD = 7601)
                          const weeklySummary = weekEntries.find(e => e.TERM_CD === '7601')
                          const dailyEntries = weekEntries.filter(e => e.TERM_CD !== '7601').sort((x, y) => {
                            const days = ["월", "화", "수", "목", "금", "토", "일"]
                            return days.indexOf(x.DY) - days.indexOf(y.DY)
                          })

                          return (
                            <div 
                              key={weekNum} 
                              style={{ 
                                padding: '16px', 
                                border: '1px solid var(--border-color)', 
                                borderRadius: '12px', 
                                background: 'rgba(255, 255, 255, 0.01)',
                                textAlign: 'left'
                              }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.04)', paddingBottom: '8px', marginBottom: '12px' }}>
                                <span style={{ fontSize: '1.1rem', fontWeight: '700' }}>
                                  <span className="gradient-text">{weekNum}주차</span> 실습 일지
                                </span>
                                <div style={{ display: 'flex', gap: '8px' }}>
                                  <button 
                                    className="btn btn-secondary" 
                                    style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                                    onClick={() => openManualWrite(weekNum)}
                                  >
                                    <Edit3 size={12} /> 수정
                                  </button>
                                  <button 
                                    className="btn btn-danger" 
                                    style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                                    onClick={() => handleManualDelete(weekNum)}
                                  >
                                    <Trash2 size={12} /> 삭제
                                  </button>
                                </div>
                              </div>

                              {weeklySummary && (
                                <div style={{ background: 'rgba(99, 102, 241, 0.05)', padding: '12px', borderRadius: '8px', border: '1px dashed rgba(99,102,241,0.2)', marginBottom: '12px' }}>
                                  <p style={{ fontSize: '0.8rem', fontWeight: '600', color: 'var(--accent-primary)', textTransform: 'uppercase' }}>주차별 종합 요약</p>
                                  <p style={{ fontSize: '0.9rem', marginTop: '4px' }}>{weeklySummary.REPORT_DESC}</p>
                                </div>
                              )}

                              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                {dailyEntries.map((day, dIdx) => (
                                  <div key={dIdx} style={{ display: 'flex', gap: '12px', fontSize: '0.85rem', padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
                                    <span style={{ width: '40px', fontWeight: '600', color: ['토','일'].includes(day.DY) ? '#f87171' : 'var(--text-secondary)' }}>
                                      {day.DY}요일
                                    </span>
                                    {day.WORK_FLAG === 'Y' ? (
                                      <>
                                        <span style={{ color: 'var(--accent-glow)', fontFamily: 'var(--font-mono)' }}>[{day.START_DATE.slice(4,6)}-{day.START_DATE.slice(6,8)}]</span>
                                        <span style={{ color: 'var(--text-muted)' }}>({day.REPORT_START_DATE ? `${day.REPORT_START_DATE.slice(0,2)}:${day.REPORT_START_DATE.slice(2,4)}` : '09:00'})</span>
                                        <span style={{ fontWeight: '500' }}>{day.REPORT_DESC}</span>
                                      </>
                                    ) : (
                                      <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>실습 없음 (N)</span>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    ) : (
                      <div style={{ padding: '40px 0', color: 'var(--text-secondary)', textAlign: 'center' }}>
                        <p>동기화된 실습일지가 존재하지 않습니다. 대시보드에서 데이터 동기화를 시도해 주세요.</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* 3. WORD CONFIG TAB */}
            {activeTab === 'words' && (
              <div className="card animated-in" style={{ textAlign: 'left' }}>
                <h3 style={{ fontSize: '1.25rem', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '12px', marginBottom: '20px' }}>
                  실습일지 랜덤 단어 및 템플릿 관리
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '24px' }}>
                  일지 생성 시 아래 단어와 패턴들이 랜덤으로 조화롭게 결합되어 문장이 만들어집니다. 단어를 클릭하면 삭제할 수 있고, 입력창을 통해 손쉽게 추가할 수 있습니다.
                </p>

                {/* Grid of Categories */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
                  {/* Adjectives */}
                  <div>
                    <h4 style={{ fontSize: '1rem', color: 'var(--accent-primary)', marginBottom: '8px' }}>형용사 (Adjectives)</h4>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
                      {words.adjectives.map((w, idx) => (
                        <span 
                          key={idx} 
                          className="badge badge-info" 
                          style={{ cursor: 'pointer', display: 'inline-flex', gap: '4px', alignItems: 'center' }}
                          onClick={() => removeWordTag('adjectives', idx)}
                        >
                          {w} <span style={{ fontSize: '10px' }}>×</span>
                        </span>
                      ))}
                    </div>
                    <div style={{ display: 'flex', gap: '10px', maxWidth: '400px' }}>
                      <input 
                        type="text" 
                        className="form-input" 
                        placeholder="새 형용사 추가 (예: 성실한)" 
                        style={{ padding: '8px 12px' }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            addWordTag('adjectives', e.target.value)
                            e.target.value = ''
                          }
                        }}
                      />
                    </div>
                  </div>

                  {/* Nouns */}
                  <div>
                    <h4 style={{ fontSize: '1rem', color: 'var(--accent-secondary)', marginBottom: '8px' }}>명사 및 실습 업무 (Nouns)</h4>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
                      {words.nouns.map((w, idx) => (
                        <span 
                          key={idx} 
                          className="badge badge-success" 
                          style={{ cursor: 'pointer', display: 'inline-flex', gap: '4px', alignItems: 'center' }}
                          onClick={() => removeWordTag('nouns', idx)}
                        >
                          {w} <span style={{ fontSize: '10px' }}>×</span>
                        </span>
                      ))}
                    </div>
                    <div style={{ display: 'flex', gap: '10px', maxWidth: '400px' }}>
                      <input 
                        type="text" 
                        className="form-input" 
                        placeholder="새 명사 추가 (예: 프론트엔드 빌드)" 
                        style={{ padding: '8px 12px' }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            addWordTag('nouns', e.target.value)
                            e.target.value = ''
                          }
                        }}
                      />
                    </div>
                  </div>

                  {/* Patterns */}
                  <div>
                    <h4 style={{ fontSize: '1rem', color: 'var(--accent-glow)', marginBottom: '8px' }}>문장 패턴 (Sentence Patterns)</h4>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                      * 템플릿 토큰: <code style={{ fontSize: '12px' }}>{`{adj}`}</code> = 형용사, <code style={{ fontSize: '12px' }}>{`{noun}`}</code> = 명사, <code style={{ fontSize: '12px' }}>{`{p}`}</code> = 을/를 조사 자동조정, <code style={{ fontSize: '12px' }}>{`{sp}`}</code> = 이/가 조사 자동조정
                    </p>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
                      {words.patterns.map((w, idx) => (
                        <span 
                          key={idx} 
                          className="badge badge-warning" 
                          style={{ cursor: 'pointer', display: 'inline-flex', gap: '4px', alignItems: 'center', textTransform: 'none' }}
                          onClick={() => removeWordTag('patterns', idx)}
                        >
                          {w} <span style={{ fontSize: '10px' }}>×</span>
                        </span>
                      ))}
                    </div>
                    <div style={{ display: 'flex', gap: '10px', maxWidth: '600px' }}>
                      <input 
                        type="text" 
                        className="form-input" 
                        placeholder="새 패턴 추가 (예: 오늘은 {noun}{p} 분석하고 {adj} 것을 공부했다)" 
                        style={{ padding: '8px 12px' }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            addWordTag('patterns', e.target.value)
                            e.target.value = ''
                          }
                        }}
                      />
                    </div>
                  </div>

                  {/* Departments */}
                  <div>
                    <h4 style={{ fontSize: '1rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>실습 부서 (Departments)</h4>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
                      {words.departments.map((w, idx) => (
                        <span 
                          key={idx} 
                          className="badge badge-info" 
                          style={{ cursor: 'pointer', display: 'inline-flex', gap: '4px', alignItems: 'center', background: 'rgba(255,255,255,0.05)', color: '#fff' }}
                          onClick={() => removeWordTag('departments', idx)}
                        >
                          {w} <span style={{ fontSize: '10px' }}>×</span>
                        </span>
                      ))}
                    </div>
                    <div style={{ display: 'flex', gap: '10px', maxWidth: '400px' }}>
                      <input 
                        type="text" 
                        className="form-input" 
                        placeholder="새 부서 추가 (예: IT전략팀)" 
                        style={{ padding: '8px 12px' }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            addWordTag('departments', e.target.value)
                            e.target.value = ''
                          }
                        }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 4. SETTINGS TAB */}
            {activeTab === 'settings' && (
              <div className="grid grid-cols-2 animated-in">
                {/* Credentials */}
                <div className="card" style={{ textAlign: 'left' }}>
                  <h3 style={{ fontSize: '1.25rem', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '12px', marginBottom: '20px' }}>
                    HIFIVE 로그인 정보
                  </h3>
                  <form onSubmit={saveCredentials}>
                    <div className="form-group">
                      <label className="form-label">아이디 (ID)</label>
                      <input 
                        type="text" 
                        className="form-input" 
                        required
                        value={credentials.user_id}
                        onChange={(e) => setCredentials({ ...credentials, user_id: e.target.value })}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">비밀번호 (PW)</label>
                      <input 
                        type="password" 
                        className="form-input" 
                        placeholder={credentials.password_masked || '새 비밀번호'}
                        value={credentials.password}
                        onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
                      />
                    </div>
                    <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '10px' }}>
                      인증 정보 저장 및 검증
                    </button>
                  </form>
                </div>

                {/* Configurations */}
                <div className="card" style={{ textAlign: 'left' }}>
                  <h3 style={{ fontSize: '1.25rem', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '12px', marginBottom: '20px' }}>
                    자동화 스케줄 및 환경설정
                  </h3>
                  <form onSubmit={saveConfig}>
                    <div className="form-group">
                      <label className="form-label">HIFIVE 홈페이지 URL</label>
                      <input 
                        type="text" 
                        className="form-input" 
                        required
                        value={config.base_url}
                        onChange={(e) => setConfig({ ...config, base_url: e.target.value })}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">매일 자동 실행 시간 (KST)</label>
                      <input 
                        type="text" 
                        className="form-input" 
                        required
                        placeholder="18:00"
                        value={config.schedule.run_time}
                        onChange={(e) => setConfig({ 
                          ...config, 
                          schedule: { ...config.schedule, run_time: e.target.value } 
                        })}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">기준 타임존 (Timezone)</label>
                      <input 
                        type="text" 
                        className="form-input" 
                        required
                        value={config.schedule.timezone}
                        onChange={(e) => setConfig({ 
                          ...config, 
                          schedule: { ...config.schedule, timezone: e.target.value } 
                        })}
                      />
                    </div>
                    <button type="submit" className="btn btn-secondary" style={{ width: '100%', marginTop: '10px' }}>
                      설정 저장
                    </button>
                  </form>
                </div>
              </div>
            )}

            {/* 5. SYSTEM LOGS TAB */}
            {activeTab === 'logs' && (
              <div className="card animated-in" style={{ textAlign: 'left' }}>
                <h3 style={{ fontSize: '1.25rem', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '12px', marginBottom: '20px', display: 'flex', alignItems: 'center', justifyItems: 'center', gap: '10px' }}>
                  <span>실습일지 자동화 실행 로그</span>
                  <button className="btn btn-secondary" style={{ marginLeft: 'auto', padding: '6px 12px', fontSize: '0.8rem' }} onClick={fetchLogs} disabled={logsLoading}>
                    {logsLoading ? <RefreshCw className="pulse-glow" size={12} /> : <RefreshCw size={12} />}
                    로그 새로고침
                  </button>
                </h3>
                <div style={{ background: '#0b0c10', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '10px', padding: '20px', overflowX: 'auto' }}>
                  <pre style={{ margin: 0, fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: '#c5c9db', whiteSpace: 'pre-wrap', lineHeight: '1.5' }}>
                    {logs || '로그 내역이 없습니다.'}
                  </pre>
                </div>
              </div>
            )}
          </>
        )}
      </main>

      {/* Footer */}
      <footer style={{ marginTop: 'auto', padding: '24px 0', borderTop: '1px solid rgba(255,255,255,0.04)', background: 'rgba(11, 12, 16, 0.9)', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
        <div className="container">
          <p>© 2026 HIFIVE Auto-LMS Service. Designed for convenience and automation.</p>
        </div>
      </footer>
    </div>
  )
}

export default App
