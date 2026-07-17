import { useState, useEffect, useCallback } from 'react'
import {
  Typography, Input, Card, Button, Modal, Form, Upload, Tag, Empty, Spin, message, Image, Space,
} from 'antd'
import { PlusOutlined, SearchOutlined, DeleteOutlined, UploadOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { listMaterials, uploadMaterial, deleteMaterial, suggestTags, API_BASE } from '../api'

export default function Materials() {
  const [materials, setMaterials] = useState([])
  const [loading, setLoading] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [suggesting, setSuggesting] = useState(false)
  const [form] = Form.useForm()
  const [file, setFile] = useState(null)

  const fetchMaterials = useCallback(async () => {
    setLoading(true)
    try {
      const res = await listMaterials(keyword)
      setMaterials(res.data || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [keyword])

  useEffect(() => {
    fetchMaterials()
  }, [fetchMaterials])

  const handleUpload = async () => {
    try {
      const values = await form.validateFields()
      if (!file) {
        message.warning('请选择文件')
        return
      }
      setUploading(true)
      const formData = new FormData()
      formData.append('file', file)
      formData.append('name', values.name)
      formData.append('tags', values.tags)
      await uploadMaterial(formData)
      message.success('上传成功')
      setModalOpen(false)
      form.resetFields()
      setFile(null)
      fetchMaterials()
    } catch (e) {
      if (e.errorFields) return
      message.error(e.message || '上传失败')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = (id, name) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除素材「${name}」吗？`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteMaterial(id)
          message.success('已删除')
          fetchMaterials()
        } catch (e) {
          message.error(e.message || '删除失败')
        }
      },
    })
  }

  const handleAutoSuggest = async () => {
    const name = form.getFieldValue('name')
    if (!name || !name.trim()) {
      message.warning('请先输入素材名称')
      return
    }
    setSuggesting(true)
    try {
      const res = await suggestTags(name.trim())
      if (res.data?.tags?.length > 0) {
        form.setFieldValue('tags', res.data.tags.join('，'))
        message.success('已自动生成标签')
      }
    } catch (e) {
      console.error(e)
    } finally {
      setSuggesting(false)
    }
  }

  const getThumbUrl = (mat) => {
    const isVideo = mat.type === 'video'
    const imgStyle = { width: '100%', height: 160, objectFit: 'cover', borderRadius: '8px 8px 0 0', background: '#f0f0f0' }
    if (isVideo) {
      return (
        <div style={{ ...imgStyle, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: '#000' }}>
          <PlayCircleOutlined style={{ fontSize: 32, color: '#fff', marginBottom: 8 }} />
          <Typography.Text style={{ color: '#fff' }}>{mat.name}</Typography.Text>
        </div>
      )
    }
    return (
      <Image
        src={API_BASE + `/uploads/${mat.file_path}`}
        alt={mat.name}
        style={imgStyle}
        fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjBmMGYwIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGRvbWluYW50LWJhc2VsaW5lPSJtaWRkbGUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZpbGw9IiNjY2MiIGZvbnQtc2l6ZT0iMTgiPueKtuaAgTwvdGV4dD48L3N2Zz4="
        preview={false}
      />
    )
  }

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography.Title level={4} style={{ margin: 0 }}>素材库</Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>上传素材</Button>
      </div>

      <Input
        placeholder="搜索素材名称或标签..."
        prefix={<SearchOutlined />}
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
        allowClear
        style={{ marginBottom: 24, maxWidth: 400 }}
      />

      {loading ? (
        <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>
      ) : materials.length === 0 ? (
        <Empty description="暂无素材" />
      ) : (
        <div className="material-grid">
          {materials.map((mat) => (
            <Card
              key={mat.id}
              className="material-card"
              cover={getThumbUrl(mat)}
              actions={[
                <DeleteOutlined key="delete" onClick={() => handleDelete(mat.id, mat.name)} />,
              ]}
              styles={{ body: { padding: 12 } }}
            >
              <Card.Meta
                title={<Typography.Text ellipsis>{mat.name}</Typography.Text>}
                description={
                  <Space wrap size={4}>
                    {mat.tags?.map((tag, i) => (
                      <Tag key={i} style={{ fontSize: 11, margin: 0 }}>{tag.trim()}</Tag>
                    ))}
                  </Space>
                }
              />
            </Card>
          ))}
        </div>
      )}

      <Modal
        title="上传素材"
        open={modalOpen}
        onCancel={() => { setModalOpen(false); form.resetFields(); setFile(null) }}
        onOk={handleUpload}
        confirmLoading={uploading}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="素材名称" rules={[{ required: true }]}>
            <Input placeholder="请输入名称" />
          </Form.Item>
          <Form.Item name="tags" label="标签（逗号分隔）" rules={[{ required: true }]}>
            <Input placeholder="例如：春天,花朵,自然" suffix={
              <Button size="small" type="link" loading={suggesting} onClick={handleAutoSuggest} style={{ padding: 0 }}>
                自动生成
              </Button>
            } />
          </Form.Item>
          <Form.Item label="文件" required>
            <Upload
              beforeUpload={(f) => { setFile(f); return false }}
              fileList={file ? [{ uid: '-1', name: file.name }] : []}
              onRemove={() => setFile(null)}
              maxCount={1}
              accept="image/*,video/*"
            >
              <Button icon={<UploadOutlined />}>选择文件</Button>
            </Upload>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
