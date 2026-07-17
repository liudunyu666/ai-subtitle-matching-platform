import { useState, useEffect, useCallback, useRef } from 'react'
import { Card, Tag, Typography, Spin, Empty, Button, Row, Col, Progress } from 'antd'
import { ReloadOutlined, PlusOutlined } from '@ant-design/icons'
import { listTasks } from '../api'

const statusConfig = {
  pending: { color: 'default', text: '等待执行' },
  processing: { color: 'processing', text: '执行中' },
  completed: { color: 'success', text: '执行成功' },
  failed: { color: 'error', text: '执行失败' },
}

function getSegmentCount(task) {
  if (!task.result) return 0
  try {
    const parsed = typeof task.result === 'string' ? JSON.parse(task.result) : task.result
    return Array.isArray(parsed) ? parsed.length : 0
  } catch {
    return 0
  }
}

export default function TaskList({ onNavigate }) {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(false)
  const pollingRef = useRef(null)

  const startPolling = useCallback(() => {
    if (pollingRef.current) clearInterval(pollingRef.current)
    pollingRef.current = setInterval(fetchTasks, 5000)
  }, []) // eslint-disable-line

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }, [])

  const fetchTasks = useCallback(async () => {
    setLoading(true)
    try {
      const res = await listTasks()
      const data = res.data || []
      setTasks(data)
      if (data.length > 0 && data.every(t => t.status === 'completed' || t.status === 'failed')) {
        stopPolling()
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [stopPolling])

  useEffect(() => {
    fetchTasks()
    startPolling()

    const handleVisibility = () => {
      if (document.hidden) {
        stopPolling()
      } else {
        fetchTasks()
        startPolling()
      }
    }
    document.addEventListener('visibilitychange', handleVisibility)

    return () => {
      stopPolling()
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [fetchTasks, startPolling, stopPolling])

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography.Title level={4} style={{ margin: 0 }}>任务列表</Typography.Title>
        <div>
          <Button icon={<ReloadOutlined />} onClick={fetchTasks} style={{ marginRight: 8 }}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => onNavigate('/upload')}>新建任务</Button>
        </div>
      </div>
      {loading && tasks.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>
      ) : tasks.length === 0 ? (
        <Empty description="暂无任务，点击「新建任务」开始" style={{ padding: 80 }}>
          <Button type="primary" onClick={() => onNavigate('/upload')}>新建任务</Button>
        </Empty>
      ) : (
        <Row gutter={[16, 16]}>
          {tasks.map((task) => {
            const cfg = statusConfig[task.status] || statusConfig.pending
            return (
              <Col xs={24} sm={12} lg={8} key={task.id}>
                <Card
                  hoverable
                  className="task-card"
                  onClick={() => onNavigate(`/task/${task.id}`)}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: 12 }}>
                    <Typography.Text strong ellipsis style={{ maxWidth: 200 }}>
                      {task.file_name || '字幕文本'}
                    </Typography.Text>
                    <Tag color={cfg.color}>{cfg.text}</Tag>
                  </div>
                  {task.status === 'processing' && (
                    <Progress percent={task.progress} size="small" />
                  )}
                  {task.status === 'failed' && (
                    <Typography.Text type="danger" style={{ fontSize: 12 }}>
                      {task.error_msg || '未知错误'}
                    </Typography.Text>
                  )}
                  {task.status === 'completed' && (
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      {getSegmentCount(task) > 0 ? `${getSegmentCount(task)} 个片段` : '已完成'}
                    </Typography.Text>
                  )}
                  <div style={{ marginTop: 8 }}>
                    <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                      {task.created_at ? new Date(task.created_at).toLocaleString() : ''}
                    </Typography.Text>
                  </div>
                </Card>
              </Col>
            )
          })}
        </Row>
      )}
    </div>
  )
}
