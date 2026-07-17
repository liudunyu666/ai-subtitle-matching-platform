import { useState, useEffect } from 'react'
import { ConfigProvider, Layout, Menu, Typography } from 'antd'
import { UnorderedListOutlined, CloudUploadOutlined, BookOutlined } from '@ant-design/icons'
import zhCN from 'antd/locale/zh_CN'
import TaskList from './pages/TaskList'
import NewTask from './pages/Upload'
import Materials from './pages/Materials'
import TaskDetail from './pages/TaskDetail'

const { Header, Content } = Layout

function App() {
  const [page, setPage] = useState('tasks')
  const [selectedTask, setSelectedTask] = useState(null)

  const navigate = (path) => {
    if (path === '/') {
      setPage('tasks')
      setSelectedTask(null)
    } else if (path.startsWith('/task/')) {
      const id = path.replace('/task/', '')
      setPage('detail')
      setSelectedTask(id)
    } else if (path === '/upload') {
      setPage('upload')
    } else if (path === '/materials') {
      setPage('materials')
    }
  }

  const menuItems = [
    { key: 'tasks', icon: <UnorderedListOutlined />, label: '任务列表' },
    { key: 'upload', icon: <CloudUploadOutlined />, label: '新建任务' },
    { key: 'materials', icon: <BookOutlined />, label: '素材库' },
  ]

  const renderPage = () => {
    switch (page) {
      case 'tasks':
        return <TaskList onNavigate={navigate} />
      case 'upload':
        return <NewTask onNavigate={navigate} />
      case 'materials':
        return <Materials />
      case 'detail':
        return <TaskDetail taskId={selectedTask} onNavigate={navigate} />
      default:
        return <TaskList onNavigate={navigate} />
    }
  }

  return (
    <ConfigProvider locale={zhCN}>
      <Layout style={{ minHeight: '100vh' }}>
        <Header
          style={{
            display: 'flex',
            alignItems: 'center',
            padding: '0 24px',
            background: '#fff',
            borderBottom: '1px solid #f0f0f0',
            position: 'sticky',
            top: 0,
            zIndex: 100,
          }}
        >
          <Typography.Title level={4} style={{ margin: 0, marginRight: 40, whiteSpace: 'nowrap' }}>
            AI 字幕分析与素材匹配
          </Typography.Title>
          <Menu
            mode="horizontal"
            selectedKeys={[page === 'detail' ? 'tasks' : page]}
            items={menuItems}
            onClick={({ key }) => navigate(key === 'tasks' ? '/' : `/${key}`)}
            style={{ flex: 1, border: 'none' }}
          />
        </Header>
        <Content>
          {renderPage()}
        </Content>
      </Layout>
    </ConfigProvider>
  )
}

export default App
