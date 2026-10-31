# 权重打包与 FTP 上传

## 操作

模型仓库 → 实验详情 → 模型产物 → 打包。选择平台并预览文件、cfg、names 和脚本后生成本地包。无需先审核实验，允许打包待审核模型。3403 根据转换记录区分 SVP/NNN；无记录时明确选择运行时。

平台与输入格式：x86（.onnx）、3403（.om）、692/530（.bin）、3588（.rknn）。这些平台名称仅用于打包，不代表平台转换工具都已接入。

包名：`weight_{模型族标识规范化}_{模型框架}_{平台}_{训练结束年月日}.tgz`。模型族标识仅保留第一个下划线；例如 `classify_two_wheel` → `classify_twowheel`。模型框架来自实验记录（旧记录允许从训练配置识别）。训练日期与当前“结束训练”使用同一时间来源 results.png，并转为 UTC+8；不使用打包当天日期。

例：`weight_classify_twowheel_hgnetv2b3_3403_20261028.tgz`。

本地布局：

```text
配置的 storage_root/
└── classify_twowheel/
    ├── weight_classify_twowheel_hgnetv2b3_3403_20261028.tgz
    └── weight_classify_twowheel_hgnetv2b3_3403_20261028/
        ├── classify_twowheel_hgnetv2b3_3403_20261028.om
        ├── classify_twowheel.cfg
        ├── classify_twowheel.names
        └── mklink.sh
```

外层模型族目录和包内 cfg/names 文件使用原始模型族标识。包内模型文件以最终包名去掉开头的 `weight_` 和末尾的 `.tgz` 后加实际模型扩展名命名，手动修改的包名同样适用；软链接目标同步更新。ONNX 的外部权重按引用的相对路径一并复制；不会执行 pt/pth 反序列化或部署脚本。脚本使用 LF，tgz 内权限明确设为 755，其余普通文件为 644。部署时解压到全局 deploy_dir，然后执行包内 mklink.sh 创建相对软链接。脚本保留目标文件存在性检查，使用 ln -sfn 更新链接，不额外阻止覆盖同名普通文件。

同名包提示覆盖或取消；确认覆盖会替换 tgz、解包目录及列表记录，更新时间、哈希和配置快照，并重置已上传标记。不保留同名包的旧历史版本。3403 SVP/NNN 使用相同平台号，会产生同名包，覆盖前需确认运行时。规范化后与其他模型族撞名时禁止跨模型族覆盖。

独立菜单“权重包管理”展示模型族、包名称、实验、平台、运行时、框架、模型尺寸、大小、FTP状态/路径、打包时间、本地路径和上传错误。支持关键词、平台、已上传状态查询，分页、下载、上传FTP。

## 配置

`backend/config/app.yaml`：

```yaml
model_packaging:
  deploy_dir: "/opt/AII/YoloModel"
  storage_root: "./data/weight-packages"
  ftp:
    enabled: false
    host: "192.168.1.149"
    port: 21
    username: ""
    password: ""
    password_env: "MLOPS_PACKAGING_FTP_PASSWORD"
    remote_dir: "/weights"
    tls: false
    passive: true
    timeout_seconds: 60
```

相对 storage_root 从 backend 目录解析。填写 username/password 后将 enabled 改为 true，重启后端加载配置。也可通过 password_env 指向的环境变量配置密码（环境变量优先）。FTP配置不会返回浏览器；服务端错误不记录密码。

上传目标：`remote_dir/原始模型族标识/包名.tgz`。只上传压缩包，不上传解包目录。先上传临时文件并检查远端大小，再重命名为正式文件。同名远端文件另行提示覆盖或取消。失败可重试，失败不会将未上传的包标记为已上传。FTPS 使用显式 TLS；本配置不支持 SFTP。

本地覆盖和上传共用跨进程文件锁，防止同时操作同一包。文件生成失败保留原有包；数据库保存失败恢复原有文件。服务器中断时操作系统释放锁，可重新尝试操作。上传状态如果因进程终止停留在“上传中”，可以再次点击上传重试。

## 接口

- `POST /mlops/weight-packages/preview`：exp_id、source_file、platform、runtime（3403 可选）。
- `POST /mlops/weight-packages`：以上参数加 preview_token、overwrite。模型或配置变化后需要重新预览。
- `GET /mlops/weight-packages`：page、page_size、keyword、platform、uploaded。
- `GET /mlops/weight-packages/{id}/download`。
- `POST /mlops/weight-packages/{id}/upload`：overwrite。

后端启动自动执行数据库迁移。通过轻量ONNX protobuf元数据读取器识别输入尺寸及外部权重引用，不依赖PyTorch或ONNX运行时。打包和上传在服务端工作线程执行，浏览器等待完成，长操作不使用默认30秒请求超时。


## 自定义名称与重新打包

包名称自动生成后允许修改（只含字母、数字、下划线、点或连字符，无路径；未输入 .tgz 时自动补全）。修改名称后刷新预览，包内根目录及软链接目标会同步采用新名称。

权重包列表的“重新打包”会带入原实验、源模型相对路径、平台、运行时和包名称，重新读取当前模型文件以及模型族当前 cfg/names 配置。保留名称时选择覆盖；修改名称时另存一包，旧包不变。原实验不需要重新导入。模型文件移动或删除时需从实验详情重新选择实际模型。

查询增加模型类型与模型族级联条件。列表增加分页序号和训练结束时间快照；旧记录迁移时从实验 results.png 回填，文件不存在则显示空。FTP显示合并为一列：未上传、上传中、已上传、上传失败，之前上传成功后重传失败显示“已上传（重传失败）”。覆盖本地包后仍重置为未上传。
