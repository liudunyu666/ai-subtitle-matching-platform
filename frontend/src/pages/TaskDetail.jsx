import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Typography, Card, Spin, Tag, Button, Progress, message, Input, Modal, Empty, Alert,
  Space, Divider, Image,
} from 'antd'
import {
  ArrowLeftOutlined, EditOutlined, CheckOutlined, CloseOutlined,
  ReloadOutlined, SearchOutlined, HolderOutlined,
} from '@ant-design/icons'
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd'
import { getTask, updateSegments, selectMaterial, listMaterials, retryTask, API_BASE } from '../api'

export default function TaskDetail({ taskId, onNavigate }) {
  const [task, setTask] = useState(null)
  const [segments, setSegments] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [editText, setEditText] = useState('')
  const [materialModal, setMaterialModal] = useState(null)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [allMaterials, setAllMaterials] = useState([])
  const [searchResults, setSearchResults] = useState([])
  const pollingRef = useRef(null)

  const computeMatch = (material, keywords) => {
    if (!keywords || keywords.length === 0) return { score: 0, matched: [], reason: '无关键词' }
    const tagList = (material.tags_str || '').split(',').map(t => t.trim().toLowerCase())
    const name = (material.name || '').toLowerCase()
    const matched = []
    for (const kw of keywords) {
      const kwLower = kw.toLowerCase()
      for (const tag of tagList) {
        if (kwLower === tag || tag.includes(kwLower) || kwLower.includes(tag)) {
          matched.push(kw)
          break
        }
      }
      if (!matched.includes(kw) && (name.includes(kwLower) || kwLower.includes(name))) {
        matched.push(kw)
      }
    }
    const score = keywords.length > 0 ? Math.round((matched.length / keywords.length) * 100) : 0
    const reason = matched.length > 0 ? `匹配到关键词：${matched.join('、')}` : '无匹配关键词'
    return { score, matchKeywords: matched, reason }
  }

  const fetchTask = useCallback(async () => {
    try {
      const res = await getTask(taskId)
      setTask(res.data)
      if (res.data.status === 'completed' && res.data.result) {
        const segs = typeof res.data.result === 'string'
          ? JSON.parse(res.data.result)
          : res.data.result
        setSegments(Array.isArray(segs) ? segs : [])
      }
      if (res.data.status === 'completed' || res.data.status === 'failed') {
        if (pollingRef.current) clearInterval(pollingRef.current)
      }
      return res.data
    } catch (e) {
      message.error('获取任务失败')
      return null
    } finally {
      setLoading(false)
    }
  }, [taskId])

  useEffect(() => {
    setLoading(true)
    fetchTask()

    const startPolling = () => {
      pollingRef.current = setInterval(async () => {
        const data = await fetchTask()
        if (data && (data.status === 'completed' || data.status === 'failed')) {
          clearInterval(pollingRef.current)
        }
      }, 2000)
    }

    startPolling()

    const handleVisibility = () => {
      if (document.hidden) {
        if (pollingRef.current) clearInterval(pollingRef.current)
      } else {
        fetchTask()
        startPolling()
      }
    }
    document.addEventListener('visibilitychange', handleVisibility)

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [fetchTask])

  const handleSaveSegments = async () => {
    setSaving(true)
    try {
      await updateSegments(taskId, segments)
      message.success('保存成功')
    } catch (e) {
      message.error(e.message || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleSelect = async (segId, materialId) => {
    try {
      await selectMaterial(taskId, segId, materialId)
      setSegments((prev) =>
        prev.map((s) =>
          s.id === segId ? { ...s, selected_material_id: materialId } : s
        )
      )
      message.success('已选择素材')
    } catch (e) {
      message.error(e.message || '选择失败')
    }
  }

  const startEdit = (seg) => {
    setEditingId(seg.id)
    setEditText(seg.text)
  }

  const saveEdit = (segId) => {
    setSegments((prev) =>
      prev.map((s) => (s.id === segId ? { ...s, text: editText } : s))
    )
    setEditingId(null)
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditText('')
  }

  const onDragEnd = (result) => {
    if (!result.destination) return
    const newSegs = Array.from(segments)
    const [removed] = newSegs.splice(result.source.index, 1)
    newSegs.splice(result.destination.index, 0, removed)
    newSegs.forEach((s, i) => { s.id = `seg_${i}` })
    setSegments(newSegs)
  }

  const handleRetry = async () => {
    setLoading(true)
    try {
      await retryTask(taskId)
      message.success('任务已重新提交')
      if (pollingRef.current) clearInterval(pollingRef.current)
      pollingRef.current = setInterval(async () => {
        const data = await fetchTask()
        if (data && (data.status === 'completed' || data.status === 'failed')) {
          clearInterval(pollingRef.current)
        }
      }, 2000)
    } catch (e) {
      message.error(e.message || '重试失败')
    } finally {
      setLoading(false)
    }
  }

  const openMaterialSearch = (seg) => {
    setMaterialModal(seg)
    setSearchKeyword('')
    setSearchResults([])
    fetchAllMaterials()
  }

  const fetchAllMaterials = async () => {
    try {
      const res = await listMaterials()
      setAllMaterials(res.data || [])
    } catch (e) {
      console.error(e)
    }
  }

  const handleSearchMaterial = async () => {
    try {
      const res = await listMaterials(searchKeyword)
      const raw = res.data || []
      const segKeywords = materialModal?.keywords || []
      const scored = raw.map(m => ({ ...m, _match: computeMatch(m, segKeywords) }))
      setSearchResults(scored)
    } catch (e) {
      console.error(e)
    }
  }

  const getSelectedMaterial = (seg) => {
    if (!seg.selected_material_id || !seg.candidates) return null
    for (const c of seg.candidates) {
      if (c.material.id === seg.selected_material_id) return c.material
    }
    return allMaterials.find((m) => m.id === seg.selected_material_id) || null
  }

  if (loading) {
    return (
      <div className="page-container" style={{ textAlign: 'center', padding: 80 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!task) {
    return (
      <div className="page-container">
        <Empty description="任务不存在">
          <Button onClick={() => onNavigate('/')}>返回列表</Button>
        </Empty>
      </div>
    )
  }

  const isProcessing = task.status === 'pending' || task.status === 'processing'
  const candidates = materialModal?.candidates || []
  const displayMaterials = searchKeyword ? searchResults : candidates

  return (
    <div className="page-container">
      <div style={{ marginBottom: 16 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => onNavigate('/')}
          type="text"
        >
          返回
        </Button>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Typography.Title level={4} style={{ margin: 0 }}>
              任务详情
            </Typography.Title>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              ID: {task.id} | {task.file_name || '字幕文本'}
            </Typography.Text>
          </div>
          <Space>
            <Tag
              color={
                task.status === 'completed' ? 'success' :
                task.status === 'failed' ? 'error' :
                task.status === 'processing' ? 'processing' : 'default'
              }
            >
              {task.status === 'pending' && '等待执行'}
              {task.status === 'processing' && '执行中'}
              {task.status === 'completed' && '执行成功'}
              {task.status === 'failed' && '执行失败'}
            </Tag>
            {isProcessing && (
              <Button icon={<ReloadOutlined />} onClick={fetchTask} size="small">刷新</Button>
            )}
          </Space>
        </div>
        {task.status === 'processing' && (
          <Progress percent={task.progress} style={{ marginTop: 12 }} />
        )}
        {task.status === 'failed' && (
          <Alert
            type="error"
            showIcon
            message="任务执行失败"
            description={task.error_msg || '未知错误'}
            style={{ marginTop: 12 }}
            action={
              <Space>
                <Button size="small" danger onClick={handleRetry}>重新执行</Button>
                <Button size="small" onClick={() => onNavigate('/upload')}>重新上传</Button>
              </Space>
            }
          />
        )}
      </Card>

      {task.status === 'completed' && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <Typography.Title level={5} style={{ margin: 0 }}>字幕片段</Typography.Title>
            <Button
              type="primary"
              onClick={handleSaveSegments}
              loading={saving}
              icon={<CheckOutlined />}
            >
              保存修改
            </Button>
          </div>

          {segments.length === 0 ? (
            <Empty description="暂无片段数据" />
          ) : (
            <DragDropContext onDragEnd={onDragEnd}>
              <Droppable droppableId="segments">
                {(provided) => (
                  <div {...provided.droppableProps} ref={provided.innerRef}>
                    {segments.map((seg, index) => {
                      const selected = getSelectedMaterial(seg)
                      return (
                        <Draggable key={seg.id} draggableId={seg.id} index={index}>
                          {(provided, snapshot) => (
                            <Card
                              ref={provided.innerRef}
                              {...provided.draggableProps}
                              className="segment-card"
                              style={{
                                marginBottom: 12,
                                borderLeft: '3px solid #1890ff',
                                ...provided.draggableProps.style,
                                opacity: snapshot.isDragging ? 0.9 : 1,
                              }}
                              size="small"
                              title={
                                <Space>
                                  <span {...provided.dragHandleProps} style={{ cursor: 'grab', color: '#999' }}>
                                    <HolderOutlined />
                                  </span>
                                  <span style={{ color: '#999' }}>片段 {index + 1}</span>
                                  {seg.keywords?.length > 0 && (
                                    <Space size={4}>
                                      {seg.keywords.map((kw, ki) => (
                                        <Tag key={ki} color="blue" style={{ fontSize: 11 }}>{kw}</Tag>
                                      ))}
                                    </Space>
                                  )}
                                </Space>
                              }
                            >
                  {editingId === seg.id ? (
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Input.TextArea
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        rows={3}
                        autoFocus
                      />
                      <Space>
                        <Button
                          type="primary"
                          size="small"
                          icon={<CheckOutlined />}
                          onClick={() => saveEdit(seg.id)}
                        >
                          确定
                        </Button>
                        <Button size="small" icon={<CloseOutlined />} onClick={cancelEdit}>取消</Button>
                      </Space>
                    </Space>
                  ) : (
                    <div
                      style={{ cursor: 'pointer', padding: '4px 0' }}
                      onClick={() => startEdit(seg)}
                    >
                      <Typography.Text>{seg.text}</Typography.Text>
                      <EditOutlined style={{ marginLeft: 8, color: '#999', fontSize: 12 }} />
                    </div>
                  )}

                  <Divider style={{ margin: '12px 0' }} />

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>候选素材</Typography.Text>
                      <Button
                        size="small"
                        icon={<SearchOutlined />}
                        onClick={() => openMaterialSearch(seg)}
                      >
                        搜索素材库
                      </Button>
                    </div>
                    {seg.candidates?.length > 0 ? (
                      seg.candidates.map((c, ci) => {
                        const isSelected = seg.selected_material_id === c.material.id
                        return (
                          <div
                            key={ci}
                            className={`candidate-item ${isSelected ? 'selected' : ''}`}
                            onClick={() => handleSelect(seg.id, c.material.id)}
                          >
                            <Image
                              src={API_BASE + `/uploads/${c.material.file_path}`}
                              alt={c.material.name}
                              width={48}
                              height={48}
                              style={{ objectFit: 'cover', borderRadius: 4, marginRight: 12 }}
                              preview={false}
                              fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDgiIGhlaWdodD0iNDgiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0iI2YwZjBmMCIvPjwvc3ZnPg=="
                            />
                            <div style={{ flex: 1 }}>
                              <Typography.Text strong style={{ fontSize: 13 }}>{c.material.name}</Typography.Text>
                              <div style={{ fontSize: 11, color: '#999' }}>
                                <Tag color={isSelected ? 'green' : 'default'} style={{ fontSize: 10 }}>
                                  {isSelected ? '已选' : `匹配度 ${(c.score * 100).toFixed(0)}%`}
                                </Tag>
                                {c.matched_keywords?.length > 0 && (
                                  <span style={{ marginLeft: 4 }}>
                                    匹配: {c.matched_keywords.join(', ')}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        )
                      })
                    ) : (
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>暂无候选素材</Typography.Text>
                    )}
                    {selected && !seg.candidates?.find(c => c.material.id === selected.id) && (
                      <div className="candidate-item selected">
                        <Image
                          src={API_BASE + `/uploads/${selected.file_path}`}
                          alt={selected.name}
                          width={48}
                          height={48}
                          style={{ objectFit: 'cover', borderRadius: 4, marginRight: 12 }}
                          preview={false}
                          fallback="data:image/svg+xml;base64,..."
                        />
                        <Typography.Text strong>{selected.name}</Typography.Text>
                        <Tag color="green" style={{ marginLeft: 8 }}>已选</Tag>
                      </div>
                    )}
                  </div>
                </Card>
                      )}
                    </Draggable>
                  )
                })
              }
                    {provided.placeholder}
                  </div>
                )}
              </Droppable>
            </DragDropContext>
          )}
        </>
      )}

      <Modal
        title="搜索素材库"
        open={!!materialModal}
        onCancel={() => setMaterialModal(null)}
        footer={null}
        width={600}
      >
        <Space style={{ width: '100%', marginBottom: 16 }}>
          <Input
            placeholder="搜索素材名称或标签..."
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            onPressEnter={handleSearchMaterial}
            style={{ flex: 1 }}
            prefix={<SearchOutlined />}
          />
          <Button type="primary" onClick={handleSearchMaterial}>搜索</Button>
        </Space>
        <div style={{ maxHeight: 400, overflow: 'auto' }}>
          {displayMaterials.length === 0 ? (
            <Empty description={searchKeyword ? '无匹配结果' : '暂无素材'} />
          ) : (
            displayMaterials.map((mat) => {
              const isSelected = materialModal?.selected_material_id === mat.id
              const matchInfo = mat._match || (mat.score != null ? { score: Math.round(mat.score * 100), matchKeywords: mat.matched_keywords, reason: mat.reason } : null)
              return (
                <div
                  key={mat.id}
                  className={`candidate-item ${isSelected ? 'selected' : ''}`}
                  onClick={() => {
                    handleSelect(materialModal.id, mat.id)
                    setMaterialModal(null)
                  }}
                >
                  <Image
                    src={API_BASE + `/uploads/${mat.file_path}`}
                    alt={mat.name}
                    width={48}
                    height={48}
                    style={{ objectFit: 'cover', borderRadius: 4, marginRight: 12 }}
                    preview={false}
                    fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDgiIGhlaWdodD0iNDgiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0iI2YwZjBmMCIvPjwvc3ZnPg=="
                  />
                  <div style={{ flex: 1 }}>
                    <Typography.Text strong>{mat.name}</Typography.Text>
                    <div>
                      {mat.tags_str?.split(',').map((tag, i) => (
                        <Tag key={i} style={{ fontSize: 11 }}>{tag.trim()}</Tag>
                      ))}
                    </div>
                    {matchInfo && (
                      <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>
                        <Tag color={matchInfo.score > 50 ? 'green' : 'default'} style={{ fontSize: 10 }}>
                          匹配度 {matchInfo.score}%
                        </Tag>
                        {matchInfo.matchKeywords?.length > 0 && (
                          <span>匹配: {matchInfo.matchKeywords.join(', ')}</span>
                        )}
                      </div>
                    )}
                  </div>
                  {isSelected && <Tag color="green">已选</Tag>}
                </div>
              )
            })
          )}
        </div>
      </Modal>
    </div>
  )
}
