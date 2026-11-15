---
layout: default
title: "如何获取 Google DeepMind 的 SatWeave 和 PARDIG 天气数据集？"
description: "SatWeave 与 PARDIG 已通过 Google Cloud Storage 开放实时流和历史档案，本文梳理数据范围、更新延迟与接入入口。"
permalink: /news/how-to-access-pardig-satweave-weather-datasets/
date: 2026-11-15
---

> 更新日期：2026-11-15 · 一手来源：[DeepMind Blog](https://deepmind.google/blog/opening-the-datasets-behind-our-ai-weather-models/)

# 如何获取 Google DeepMind 的 SatWeave 和 PARDIG 天气数据集？

先给结论：SatWeave 和 PARDIG 都放在 **Google Cloud Storage** 上，格式是 Zarr v3，许可是 CC BY 4.0，**有 Google Cloud 账号就能读，不用填数据申请表**。SatWeave 的桶是 `gs://satweave_1/`，PARDIG 的桶是 `gs://pardig_1/`；PARDIG 另外在 **Google Earth Engine** 有两个静态归档集合。要最新数据走 Cloud Storage，Earth Engine 上的 PARDIG 不会持续更新。

本文适合要搭建天气、降水、洪水、干旱或太阳能相关数据管线的研究者和开发者。路径、资产 ID、延迟和坐标约定全部来自 Google 官方材料：DeepMind 发布文章 [Opening the datasets behind our AI weather models](https://deepmind.google/blog/opening-the-datasets-behind-our-ai-weather-models/)，以及 WeatherNext 开发者文档里的 [SatWeave 页](https://developers.google.com/weathernext/guides/satweave) 和 [PARDIG 页](https://developers.google.com/weathernext/guides/pardig)。

## 先判断：你需要哪一种数据？

Google DeepMind 在 2026 年 11 月宣布开放这两个数据集，它们也是 WeatherNext 3 模型使用的数据。SatWeave 是卫星观测拼图，PARDIG 是 AI 推算的全球降水。

| 数据集 | 内容 | 时间分辨率 | 空间分辨率 | 时间范围 | 实时延迟 | 获取位置 |
|---|---|---|---|---|---|---|
| SatWeave | 5 个地球静止卫星位置拼成的全球影像，17 个波段 | 2016–2025 归档 30 分钟；2026 年起 1 小时 | 0.1°（约 10 公里） | 2016 年至今 | 约 1 小时 | Cloud Storage `gs://satweave_1/` |
| PARDIG-NRT（近实时） | 全球降水率 | 15 分钟 | 0.1°（约 10 公里） | 2016 年至今 | 每 6 小时一批，平均约 5 小时，实际约 2～8 小时 | Cloud Storage `gs://pardig_1/NRT/`；Earth Engine 静态归档 |
| PARDIG-LR（长序列） | 全球降水率 | 15 分钟 | 0.1°（约 10 公里） | 1999–2023 | 静态归档，不更新 | Cloud Storage `gs://pardig_1/LR/`；Earth Engine |

选择建议来自 PARDIG 官方文档：做业务用途或只需要 2016 年以后的数据，优先用 PARDIG-NRT；需要从 1999 年开始的长序列，再用 PARDIG-LR，或把 LR 与 NRT 拼起来用，但要注意两者输入数据的分辨率不同。

## 从 Google Cloud Storage 读取 SatWeave

SatWeave 的目录结构（官方文档给出）：

| 路径 | 内容 |
|---|---|
| `gs://satweave_1/zarr/2016_to_2025/mosaic.zarr` | 历史归档，2016-01-01T00:00 到 2025-12-31T23:30（UTC），每 30 分钟一帧 |
| `gs://satweave_1/zarr/2026_to_present/<YYYYMMDDTHHMMSS>/mosaic.zarr` | 2026 年起的补录和实时数据，每小时一个目录，每个目录一帧 |

17 个波段分两类：7 个可见光、近红外、短波红外反射率波段（变量名如 `mosaic_640_nm`，单位 0～100 %），10 个短波、水汽和热红外亮温波段（如 `mosaic_11200_nm`，单位 K）。

官方示例用 `xarray` + `zarr` + `obstore` 懒加载，先安装：`pip install xarray zarr obstore`。打开某个小时的数据：

```python
import obstore
import xarray as xr
import zarr

gcs_store = obstore.store.GCSStore(
    bucket="satweave_1",
    prefix="zarr/2026_to_present/20260901T120000/mosaic.zarr",
)
ds = xr.open_zarr(zarr.storage.ObjectStore(gcs_store), chunks={})
print(ds)
```

要读历史归档，把 `prefix` 换成 `zarr/2016_to_2025/mosaic.zarr`。官方说明两部分的变量属性和坐标网格一致，可以直接沿 `time` 维拼接。

## 从 Google Cloud Storage 读取 PARDIG

PARDIG 只有一个变量 `precipitation`：某一时刻的瞬时降水率，`float32`，**单位是 m/h**，乘以 1000 才是常用的 mm/h。主要路径：

| 路径 | 用途 |
|---|---|
| `gs://pardig_1/NRT/zarr/2016_to_2025/predictions.zarr` | NRT 多年归档，从 2016-01-01T07:45 UTC 开始 |
| `gs://pardig_1/NRT/zarr/2026_to_present/<YYYYMMDDTHHMMSS>/predictions.zarr` | 实时数据，每个目录一帧 |
| `gs://pardig_1/NRT/zarr_rechunked_as_timeseries/2016_to_2025/predictions.zarr` | 按时间序列重新分块，适合取单点长序列 |
| `gs://pardig_1/LR/zarr/1999_to_2023/predictions.zarr` | LR 长序列，适合按时间取整张图 |
| `gs://pardig_1/LR/zarr_rechunked_as_timeseries/1999_to_2023/predictions.zarr` | LR 按时间序列分块 |

打开方式和 SatWeave 相同，只是换桶和前缀：

```python
gcs_store = obstore.store.GCSStore(
    bucket="pardig_1",
    prefix="NRT/zarr/2016_to_2025/predictions.zarr",
)
ds = xr.open_zarr(zarr.storage.ObjectStore(gcs_store), chunks={})
```

官方给出的 NRT 多年归档总大小约 9 TB，`chunks={}` 是懒加载，先用 `print(ds)` 看结构，再按时间和区域切小块计算，不要整体下载。

## 从 Google Earth Engine 使用 PARDIG

PARDIG 在 Earth Engine 公开数据目录里有两个 `ImageCollection`：

| 集合 | 资产 ID | 时间范围 |
|---|---|---|
| PARDIG-NRT | `projects/gcp-public-data-weathernext/assets/PARDIG_1_NRT` | 2016-01-01T07:45Z 到 2026 年 10 月（上线时的静态归档） |
| PARDIG-LR | `projects/gcp-public-data-weathernext/assets/PARDIG_1_LR` | 1999-01-01T00:00Z 到 2023-12-31T23:45Z（静态归档） |

官方示例（Python API，`YOUR_PROJECT_ID` 换成你自己的 Google Cloud 项目）：

```python
import ee

ee.Initialize(project="YOUR_PROJECT_ID")
frame = (
    ee.ImageCollection("projects/gcp-public-data-weathernext/assets/PARDIG_1_NRT")
    .filterDate("2024-09-26T12:00:00Z", "2024-09-26T12:15:00Z")
    .first()
    .select("precipitation")
)
rate_mm_hr = frame.multiply(1000.0)
```

SatWeave 官方文档只列了 Cloud Storage 一个获取位置，没有 Earth Engine 资产。

## 找不到数据、数据对不上时的排查顺序

1. **Earth Engine 里查不到最近的 PARDIG**：两个集合都是静态归档，NRT 只到 2026 年 10 月。要持续更新的数据，按官方说明去读 `gs://pardig_1/NRT/zarr/2026_to_present/`。
2. **最新一帧比当前时间晚好几个小时**：PARDIG-NRT 跟随 ECMWF HRES 分析周期（00、06、12、18 UTC），每 6 小时一次性生成 6 小时共 24 帧。发布时最新一帧约晚 2 小时，最早一帧约晚 7.5～8 小时，平均约 5 小时，这是正常现象。SatWeave 实时延迟约 1 小时。
3. **数值看起来小了一千倍**：PARDIG 单位是 m/h，乘 1000 换成 mm/h。官方还说明 15 分钟瞬时降水率上限是 75 mm/h（0.075 m/h），局地强对流峰值可能被截平。
4. **经纬度取错位置**：两个数据集的 Zarr 经度都是 0～359.9°E，西经要用 `lon % 360` 换算。纬度方向不同：PARDIG 的 Zarr 是从南到北（-90 到 90），SatWeave 是从北到南（90 到 -90）；PARDIG 在 Earth Engine 里又是从北到南、经度 -180～179.9。按纬度切片前先打印坐标确认方向。
5. **SatWeave 大片是 NaN**：地球静止卫星只看得到约南北纬 60°～65° 以内，更高纬度、夜间的反射率波段、某颗卫星没有的波段都记为 NaN。例如 `mosaic_509_nm` 只有 Himawari 有，`mosaic_1370_nm` 只有两颗 GOES 有。2016—2018 年西半球还经历过旧 GOES 到新传感器的过渡，早期部分波段缺失更多。
6. **读不了桶**：官方说的是"任何已认证的 Google Cloud 账号"可读，不用申请表。先确认本机已登录 Google Cloud 账号、Earth Engine 已用自己的项目初始化。

## 用于告警或业务决策前的提醒

PARDIG 官方条款写明：它是仍在研究中的实验性 AI 数据集，按原样提供，**不是官方气象观测、预报或预警**，不要把它当作保护生命财产的唯一依据，应以所在国家气象部门和当地应急部门的官方预警为准。SatWeave 官方也说明单帧可能有扫描线缺失、拼接边界定标差异、太阳耀斑等瑕疵，使用前要检查 NaN 和异常值。

两个数据集都按 CC BY 4.0 授权，使用时按许可要求注明来源；PARDIG 的研究论文见 [arXiv:2611.13941](https://arxiv.org/abs/2611.13941)。

## 接入前检查清单

- [ ] 已确定用 SatWeave、PARDIG-NRT 还是 PARDIG-LR；
- [ ] 要实时数据的，读的是 Cloud Storage 的 `2026_to_present/`，不是 Earth Engine 静态归档；
- [ ] 已把 PARDIG 的 m/h 换算成 mm/h；
- [ ] 已按各自的纬度方向和 0～360 经度切片；
- [ ] 调度周期按 SatWeave 每小时、PARDIG-NRT 每 6 小时一批来设；
- [ ] 已先用一个时间点、一个小区域验证读取结果，再跑大范围批处理；
- [ ] 已记录数据集名称、路径、访问日期，并按 CC BY 4.0 注明来源。

如果你的数据管线还需要调用大模型 API 做摘要或分析，可以在 OpenLux [注册并创建 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=how-to-access-pardig-satweave-weather-datasets&utm_content=footer)；SatWeave 和 PARDIG 本身直接从 Google 官方获取，不经过 OpenLux。

**官方一手来源**

- https://deepmind.google/blog/opening-the-datasets-behind-our-ai-weather-models/
- https://developers.google.com/weathernext/guides/satweave
- https://developers.google.com/weathernext/guides/pardig

## 同专题文章

- [中转站检测：怎么判断 API 中转站是不是官方原模型（6 个自测方法，含降智排查）](https://a37836323.github.io/openlux-api-guides/news/check-api-relay-real-model/)
- [llama.cpp 升级 v1.0.0 会破坏 C API/ABI 吗？如何固定 libllama/libggml 版本并安排迁移](https://a37836323.github.io/openlux-api-guides/news/llama-cpp-v1-api-abi-migration/)
- [如何用 Hugging Face Jobs 微调 TRELLIS.2？遇到“需要 HF_TOKEN 和 DINOv3 权限”怎么处理](https://a37836323.github.io/openlux-api-guides/news/how-to-finetune-trellis2-with-hugging-face-jobs/)
- [Cosmos3-Sim-Bimanual 如何用 vLLM-Omni 推理？59 个动作控制值怎么补齐、如何与输入帧对齐？](https://a37836323.github.io/openlux-api-guides/news/cosmos3-sim-bimanual-vllm-omni-inference/)
- [Transformers 如何调用 Phonon TTS？先核对模型许可和版本](https://a37836323.github.io/openlux-api-guides/news/hugging-face-phonon-transformers-integration/)
- [grok-imagine-image-quality 11 月 2 日退役：请求会转到 grok-imagine-image-2.0 的 low 档，要不要改 model 和 quality](https://a37836323.github.io/openlux-api-guides/news/grok-imagine-image-quality-retirement-image-2-0-migration/)

[查看「其他模型与通用实践」全部文章](https://a37836323.github.io/openlux-api-guides/topics/general/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)
