<!-- src/pages/Automation.vue -->
<template>
  <div class="space-y-4">
    <div class="card p-4">
      <div class="flex items-center justify-between">
        <div>
          <div class="text-lg font-semibold text-slate-900">自动化规则引擎</div>
          <div class="text-sm text-slate-500 mt-1">定义条件触发自动动作，实现智能控制</div>
        </div>
        <div class="flex items-center gap-2">
          <button class="btn" @click="refreshRules">
            <RefreshCw class="w-4 h-4" /> 刷新
          </button>
          <button class="btn btn-primary" @click="showCreateModal = true">
            <Plus class="w-4 h-4" /> 新建规则
          </button>
        </div>
      </div>
    </div>

    <!-- 状态概览 -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="card p-4">
        <div class="text-sm text-slate-500">总规则数</div>
        <div class="text-2xl font-semibold text-slate-900 mt-2">{{ status.total_rules }}</div>
      </div>
      <div class="card p-4">
        <div class="text-sm text-slate-500">启用规则</div>
        <div class="text-2xl font-semibold text-slate-900 mt-2">{{ status.enabled_rules }}</div>
      </div>
      <div class="card p-4">
        <div class="text-sm text-slate-500">总触发次数</div>
        <div class="text-2xl font-semibold text-slate-900 mt-2">{{ status.total_triggers }}</div>
      </div>
      <div class="card p-4">
        <div class="text-sm text-slate-500">上次检查</div>
        <div class="text-2xl font-semibold text-slate-900 mt-2">{{ formatTimeShort(status.last_checked) }}</div>
      </div>
    </div>

    <!-- 规则列表 -->
    <div class="card p-4">
      <div class="text-sm font-semibold text-slate-900 mb-4">规则列表</div>

      <div class="space-y-3">
        <div
          v-for="rule in rules"
          :key="rule.id"
          class="border border-slate-200 rounded-xl p-4 hover:bg-slate-50 transition"
        >
          <div class="flex items-start justify-between gap-4">
            <div class="flex-1">
              <div class="flex items-center gap-2 mb-2">
                <span class="chip" :class="rule.enabled ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-slate-50 text-slate-600'">
                  {{ rule.enabled ? '启用' : '禁用' }}
                </span>
                <div class="text-sm font-semibold text-slate-900">{{ rule.name }}</div>
              </div>

              <div class="text-xs text-slate-600 mb-3">
                <div class="mb-1">
                  <span class="font-medium">条件：</span>
                  <span>{{ formatCondition(rule.condition) }}</span>
                </div>
                <div>
                  <span class="font-medium">动作：</span>
                  <span>{{ formatActions(rule.actions) }}</span>
                </div>
              </div>

              <div class="flex items-center gap-4 text-xs text-slate-500">
                <span>触发 {{ rule.trigger_count }} 次</span>
                <span v-if="rule.last_triggered">最后触发 {{ formatTimeAgo(rule.last_triggered) }}</span>
                <span>冷却 {{ rule.cooldown_seconds }} 秒</span>
              </div>
            </div>

            <div class="flex items-center gap-2">
              <button class="btn" @click="testRule(rule.id)" title="测试规则">
                <Play class="w-4 h-4" />
              </button>
              <button class="btn" @click="triggerRule(rule.id)" title="手动触发">
                <Zap class="w-4 h-4" />
              </button>
              <button class="btn" @click="editRule(rule)" title="编辑">
                <Edit class="w-4 h-4" />
              </button>
              <button class="btn" @click="toggleRule(rule)" title="启用/禁用">
                <ToggleRight v-if="rule.enabled" class="w-4 h-4" />
                <ToggleLeft v-else class="w-4 h-4" />
              </button>
              <button class="btn" @click="deleteRule(rule.id)" title="删除">
                <Trash2 class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        <div v-if="rules.length === 0" class="text-center py-8 text-slate-500">
          暂无规则，点击"新建规则"按钮创建
        </div>
      </div>
    </div>

    <!-- 创建/编辑规则模态框 -->
    <div v-if="showCreateModal || editingRule" class="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div class="p-6">
          <div class="text-lg font-semibold text-slate-900 mb-4">
            {{ editingRule ? '编辑规则' : '新建规则' }}
          </div>

          <div class="space-y-4">
            <!-- 基本设置 -->
            <div>
              <label class="block text-sm text-slate-700 mb-2">规则名称</label>
              <input v-model="newRule.name" type="text" class="btn w-full" placeholder="例如：温度过高自动通风">
            </div>

            <div class="flex items-center gap-2">
              <input v-model="newRule.enabled" type="checkbox" id="enabled" class="rounded">
              <label for="enabled" class="text-sm text-slate-700">启用规则</label>
            </div>

            <div>
              <label class="block text-sm text-slate-700 mb-2">冷却时间（秒）</label>
              <input v-model.number="newRule.cooldown_seconds" type="number" min="0" max="3600" class="btn w-full" placeholder="300">
              <div class="text-xs text-slate-500 mt-1">防止规则频繁触发，建议300秒（5分钟）</div>
            </div>

            <!-- 条件设置 -->
            <div class="pt-4 border-t">
              <div class="text-sm font-semibold text-slate-900 mb-3">触发条件</div>

              <div class="space-y-3">
                <div>
                  <label class="block text-sm text-slate-700 mb-2">条件类型</label>
                  <select v-model="newRule.condition.type" class="btn w-full" @change="resetCondition">
                    <option value="sensor_threshold">传感器阈值</option>
                    <option value="time_based">时间条件</option>
                    <option value="compound">复合条件</option>
                  </select>
                </div>

                <!-- 传感器阈值条件 -->
                <div v-if="newRule.condition.type === 'sensor_threshold'" class="space-y-3">
                  <div>
                    <label class="block text-sm text-slate-700 mb-2">传感器</label>
                    <select v-model="newRule.condition.sensor_id" class="btn w-full">
                      <option v-for="sensor in sensors" :key="sensor.id" :value="sensor.id">
                        {{ sensor.room }} · {{ sensor.name }} ({{ sensor.id }})
                      </option>
                    </select>
                  </div>

                  <div class="grid grid-cols-2 gap-3">
                    <div>
                      <label class="block text-sm text-slate-700 mb-2">比较运算符</label>
                      <select v-model="newRule.condition.operator" class="btn w-full">
                        <option value=">">大于</option>
                        <option value=">=">大于等于</option>
                        <option value="<">小于</option>
                        <option value="<=">小于等于</option>
                        <option value="==">等于</option>
                      </select>
                    </div>

                    <div>
                      <label class="block text-sm text-slate-700 mb-2">阈值</label>
                      <input v-model.number="newRule.condition.value" type="number" step="0.1" class="btn w-full">
                    </div>
                  </div>

                  <div>
                    <label class="block text-sm text-slate-700 mb-2">持续时间（秒）</label>
                    <input v-model.number="newRule.condition.duration" type="number" min="0" max="3600" class="btn w-full" placeholder="60">
                    <div class="text-xs text-slate-500 mt-1">条件需要持续满足的时间，0表示立即触发</div>
                  </div>
                </div>

                <!-- 时间条件 -->
                <div v-if="newRule.condition.type === 'time_based'" class="space-y-3">
                  <div>
                    <label class="block text-sm text-slate-700 mb-2">时间范围</label>
                    <div class="flex items-center gap-2">
                      <input v-model="timeStart" type="time" class="btn">
                      <span>至</span>
                      <input v-model="timeEnd" type="time" class="btn">
                    </div>
                  </div>

                  <div>
                    <label class="block text-sm text-slate-700 mb-2">生效日期</label>
                    <div class="flex flex-wrap gap-2">
                      <label v-for="day in daysOfWeek" :key="day.value" class="flex items-center gap-1">
                        <input
                          type="checkbox"
                          v-model="selectedDays"
                          :value="day.value"
                          class="rounded"
                        >
                        <span class="text-sm text-slate-700">{{ day.label }}</span>
                      </label>
                    </div>
                  </div>
                </div>

                <!-- 复合条件 -->
                <div v-if="newRule.condition.type === 'compound'" class="space-y-3">
                  <div>
                    <label class="block text-sm text-slate-700 mb-2">逻辑运算符</label>
                    <select v-model="newRule.condition.operator" class="btn w-full">
                      <option value="AND">与 (AND) - 所有条件都满足</option>
                      <option value="OR">或 (OR) - 任意条件满足</option>
                    </select>
                  </div>

                  <div class="border border-slate-200 rounded-xl p-3">
                    <div class="text-sm font-medium text-slate-700 mb-2">子条件</div>
                    <div class="space-y-3">
                      <div v-for="(subCond, index) in newRule.condition.conditions" :key="index" class="flex items-start gap-2">
                        <div class="flex-1 space-y-2">
                          <select v-model="subCond.type" class="btn w-full" @change="resetSubCondition(index)">
                            <option value="sensor_threshold">传感器阈值</option>
                            <option value="time_based">时间条件</option>
                          </select>

                          <div v-if="subCond.type === 'sensor_threshold'" class="grid grid-cols-3 gap-2">
                            <select v-model="subCond.sensor_id" class="btn">
                              <option v-for="sensor in sensors" :key="sensor.id" :value="sensor.id">
                                {{ sensor.id }}
                              </option>
                            </select>
                            <select v-model="subCond.operator" class="btn">
                              <option value=">">></option>
                              <option value=">=">>=</option>
                              <option value="<"><</option>
                              <option value="<="><=</option>
                              <option value="==">==</option>
                            </select>
                            <input v-model.number="subCond.value" type="number" step="0.1" class="btn" placeholder="值">
                          </div>

                          <div v-if="subCond.type === 'time_based'" class="grid grid-cols-2 gap-2">
                            <input v-model="subCond.time_range" type="text" class="btn" placeholder="HH:MM-HH:MM">
                            <input v-model="subCond.days_of_week" type="text" class="btn" placeholder="1,2,3,4,5">
                          </div>
                        </div>

                        <button class="btn" @click="removeSubCondition(index)" title="删除">
                          <Trash2 class="w-4 h-4" />
                        </button>
                      </div>

                      <button class="btn w-full" @click="addSubCondition">
                        <Plus class="w-4 h-4" /> 添加子条件
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 动作设置 -->
            <div class="pt-4 border-t">
              <div class="text-sm font-semibold text-slate-900 mb-3">执行动作</div>

              <div class="space-y-3">
                <div v-for="(action, index) in newRule.actions" :key="index" class="flex items-start gap-2">
                  <div class="flex-1 space-y-2">
                    <select v-model="action.type" class="btn w-full" @change="resetAction(index)">
                      <option value="set_actuator">设置执行器</option>
                      <option value="send_notification">发送通知</option>
                      <option value="log_event">记录事件</option>
                    </select>

                    <!-- 设置执行器动作 -->
                    <div v-if="action.type === 'set_actuator'" class="grid grid-cols-2 gap-2">
                      <select v-model="action.actuator" class="btn">
                        <option value="lights">灯光</option>
                        <option value="ventilation">通风</option>
                        <option value="purifier">净化器</option>
                        <option value="target_temp">目标温度</option>
                      </select>
                      <input
                        v-if="action.actuator === 'target_temp'"
                        v-model.number="action.value"
                        type="number"
                        step="0.5"
                        min="16"
                        max="30"
                        class="btn"
                        placeholder="温度值"
                      >
                      <select v-else v-model="action.value" class="btn">
                        <option :value="true">开启</option>
                        <option :value="false">关闭</option>
                      </select>
                    </div>

                    <!-- 发送通知动作 -->
                    <div v-if="action.type === 'send_notification'">
                      <input v-model="action.message" type="text" class="btn w-full" placeholder="通知消息内容">
                    </div>

                    <!-- 记录事件动作 -->
                    <div v-if="action.type === 'log_event'" class="grid grid-cols-2 gap-2">
                      <input v-model="action.message" type="text" class="btn" placeholder="事件消息">
                      <select v-model="action.level" class="btn">
                        <option value="info">信息</option>
                        <option value="warn">警告</option>
                        <option value="alarm">告警</option>
                      </select>
                    </div>
                  </div>

                  <button class="btn" @click="removeAction(index)" title="删除">
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>

                <button class="btn w-full" @click="addAction">
                  <Plus class="w-4 h-4" /> 添加动作
                </button>
              </div>
            </div>

            <!-- 按钮 -->
            <div class="flex justify-end gap-3 pt-4">
              <button class="btn" @click="cancelEdit">取消</button>
              <button class="btn btn-primary" @click="saveRule">
                {{ editingRule ? '更新规则' : '创建规则' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  RefreshCw, Plus, Play, Zap, Edit, Trash2,
  ToggleRight, ToggleLeft
} from 'lucide-vue-next'
import { useStore } from '../lib/store'

const { state } = useStore()

// 状态
const rules = ref([])
const status = ref({
  total_rules: 0,
  enabled_rules: 0,
  total_triggers: 0,
  last_checked: ''
})

// 模态框状态
const showCreateModal = ref(false)
const editingRule = ref(null)

// 新规则数据
const newRule = ref({
  name: '',
  enabled: true,
  condition: {
    type: 'sensor_threshold',
    sensor_id: '',
    operator: '>',
    value: 0,
    duration: 60
  },
  actions: [{
    type: 'send_notification',
    message: ''
  }],
  cooldown_seconds: 300
})

// 时间条件相关
const timeStart = ref('06:00')
const timeEnd = ref('08:00')
const selectedDays = ref([1, 2, 3, 4, 5])

const daysOfWeek = [
  { value: 1, label: '周一' },
  { value: 2, label: '周二' },
  { value: 3, label: '周三' },
  { value: 4, label: '周四' },
  { value: 5, label: '周五' },
  { value: 6, label: '周六' },
  { value: 7, label: '周日' }
]

// 计算属性
const sensors = computed(() => state.sensors || [])

// 方法
async function refreshRules() {
  try {
    const apiBase = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8001'

    // 获取规则列表
    const rulesRes = await fetch(`${apiBase}/api/automation/rules`)
    rules.value = await rulesRes.json()

    // 获取状态
    const statusRes = await fetch(`${apiBase}/api/automation/status`)
    status.value = await statusRes.json()

  } catch (error) {
    console.error('刷新规则失败:', error)
  }
}

function formatCondition(condition) {
  if (!condition) return '未知条件'

  if (condition.type === 'sensor_threshold') {
    const sensor = sensors.value.find(s => s.id === condition.sensor_id)
    const sensorName = sensor ? `${sensor.room}·${sensor.name}` : condition.sensor_id
    return `${sensorName} ${condition.operator} ${condition.value}${sensor?.unit || ''}，持续${condition.duration || 0}秒`
  }

  if (condition.type === 'time_based') {
    const daysMap = {1:'一',2:'二',3:'三',4:'四',5:'五',6:'六',7:'日'}
    const days = condition.days_of_week?.map(d => daysMap[d] || d).join('、') || '每天'
    return `时间 ${condition.time_range}，星期${days}`
  }

  if (condition.type === 'compound') {
    return `${condition.operator} 条件（${condition.conditions?.length || 0}个子条件）`
  }

  return JSON.stringify(condition)
}

function formatActions(actions) {
  if (!actions || actions.length === 0) return '无动作'

  const actionTexts = actions.map(action => {
    if (action.type === 'set_actuator') {
      const actuatorMap = {
        lights: '灯光',
        ventilation: '通风',
        purifier: '净化器',
        target_temp: '目标温度'
      }
      return `${actuatorMap[action.actuator] || action.actuator} 设为 ${action.value}`
    }
    if (action.type === 'send_notification') {
      return `发送通知：${action.message.substring(0, 20)}...`
    }
    if (action.type === 'log_event') {
      return `记录${action.level}事件`
    }
    return action.type
  })

  return actionTexts.join('；')
}

function formatTimeAgo(timestamp) {
  if (!timestamp) return '从未'

  const now = new Date()
  const time = new Date(timestamp)
  const diffMs = now - time
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins}分钟前`
  if (diffHours < 24) return `${diffHours}小时前`
  return `${diffDays}天前`
}

function formatTimeShort(timestamp) {
  if (!timestamp) return '--'
  return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function resetCondition() {
  const type = newRule.value.condition.type

  if (type === 'sensor_threshold') {
    newRule.value.condition = {
      type,
      sensor_id: sensors.value[0]?.id || '',
      operator: '>',
      value: 0,
      duration: 60
    }
  } else if (type === 'time_based') {
    newRule.value.condition = {
      type,
      time_range: `${timeStart.value}-${timeEnd.value}`,
      days_of_week: selectedDays.value
    }
  } else if (type === 'compound') {
    newRule.value.condition = {
      type,
      operator: 'AND',
      conditions: []
    }
  }
}

function resetSubCondition(index) {
  const subCond = newRule.value.condition.conditions[index]
  const type = subCond.type

  if (type === 'sensor_threshold') {
    newRule.value.condition.conditions[index] = {
      type,
      sensor_id: sensors.value[0]?.id || '',
      operator: '>',
      value: 0
    }
  } else if (type === 'time_based') {
    newRule.value.condition.conditions[index] = {
      type,
      time_range: '06:00-08:00',
      days_of_week: [1, 2, 3, 4, 5]
    }
  }
}

function resetAction(index) {
  const action = newRule.value.actions[index]
  const type = action.type

  if (type === 'set_actuator') {
    newRule.value.actions[index] = {
      type,
      actuator: 'lights',
      value: true
    }
  } else if (type === 'send_notification') {
    newRule.value.actions[index] = {
      type,
      message: ''
    }
  } else if (type === 'log_event') {
    newRule.value.actions[index] = {
      type,
      message: '',
      level: 'info'
    }
  }
}

function addSubCondition() {
  if (!newRule.value.condition.conditions) {
    newRule.value.condition.conditions = []
  }

  newRule.value.condition.conditions.push({
    type: 'sensor_threshold',
    sensor_id: sensors.value[0]?.id || '',
    operator: '>',
    value: 0
  })
}

function removeSubCondition(index) {
  newRule.value.condition.conditions.splice(index, 1)
}

function addAction() {
  newRule.value.actions.push({
    type: 'send_notification',
    message: ''
  })
}

function removeAction(index) {
  newRule.value.actions.splice(index, 1)
}

function editRule(rule) {
  editingRule.value = rule
  newRule.value = JSON.parse(JSON.stringify(rule))

  // 处理时间条件
  if (rule.condition.type === 'time_based') {
    const [start, end] = rule.condition.time_range.split('-')
    timeStart.value = start
    timeEnd.value = end
    selectedDays.value = rule.condition.days_of_week || [1, 2, 3, 4, 5]
  }
}

function cancelEdit() {
  showCreateModal.value = false
  editingRule.value = null
  resetNewRule()
}

function resetNewRule() {
  newRule.value = {
    name: '',
    enabled: true,
    condition: {
      type: 'sensor_threshold',
      sensor_id: sensors.value[0]?.id || '',
      operator: '>',
      value: 0,
      duration: 60
    },
    actions: [{
      type: 'send_notification',
      message: ''
    }],
    cooldown_seconds: 300
  }
}

async function saveRule() {
  try {
    // 准备条件数据
    const condition = { ...newRule.value.condition }

    if (condition.type === 'time_based') {
      condition.time_range = `${timeStart.value}-${timeEnd.value}`
      condition.days_of_week = selectedDays.value
    }

    const ruleData = {
      ...newRule.value,
      condition
    }

    const apiBase = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8001'

    if (editingRule.value) {
      // 更新规则
      const response = await fetch(`${apiBase}/api/automation/rules/${editingRule.value.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ruleData)
      })

      if (!response.ok) throw new Error('更新失败')
    } else {
      // 创建规则
      const response = await fetch(`${apiBase}/api/automation/rules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ruleData)
      })

      if (!response.ok) throw new Error('创建失败')
    }

    // 刷新列表
    await refreshRules()

    // 关闭模态框
    showCreateModal.value = false
    editingRule.value = null
    resetNewRule()

  } catch (error) {
    console.error('保存规则失败:', error)
    alert('保存失败：' + error.message)
  }
}

async function toggleRule(rule) {
  try {
    const apiBase = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8001'

    const response = await fetch(`${apiBase}/api/automation/rules/${rule.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: !rule.enabled })
    })

    if (response.ok) {
      await refreshRules()
    }
  } catch (error) {
    console.error('切换规则状态失败:', error)
  }
}

async function testRule(ruleId) {
  try {
    const apiBase = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8001'

    const response = await fetch(`${apiBase}/api/automation/rules/${ruleId}/test`, {
      method: 'POST'
    })

    const result = await response.json()

    if (result.ok) {
      alert(`规则条件${result.condition_met ? '满足' : '不满足'}`)
    } else {
      alert('测试失败：' + result.error)
    }
  } catch (error) {
    console.error('测试规则失败:', error)
    alert('测试失败：' + error.message)
  }
}

async function triggerRule(ruleId) {
  try {
    const apiBase = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8001'

    const response = await fetch(`${apiBase}/api/automation/rules/${ruleId}/trigger`, {
      method: 'POST'
    })

    const result = await response.json()

    if (result.ok) {
      alert('规则已手动触发')
      await refreshRules()
    } else {
      alert('触发失败：' + result.error)
    }
  } catch (error) {
    console.error('触发规则失败:', error)
    alert('触发失败：' + error.message)
  }
}

async function deleteRule(ruleId) {
  if (!confirm('确定要删除这个规则吗？')) return

  try {
    const apiBase = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8001'

    const response = await fetch(`${apiBase}/api/automation/rules/${ruleId}`, {
      method: 'DELETE'
    })

    const result = await response.json()

    if (result.ok) {
      await refreshRules()
    } else {
      alert('删除失败：' + result.error)
    }
  } catch (error) {
    console.error('删除规则失败:', error)
    alert('删除失败：' + error.message)
  }
}

// 初始化
onMounted(async () => {
  await refreshRules()

  // 设置默认传感器
  if (sensors.value.length > 0) {
    newRule.value.condition.sensor_id = sensors.value[0].id
  }
})
</script>