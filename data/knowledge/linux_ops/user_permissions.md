# Linux 用户与权限管理

## 用户管理命令
```bash
useradd -m -s /bin/bash username    # 创建用户
userdel -r username                 # 删除用户及其目录
usermod -aG groupname username      # 将用户添加到组
passwd username                     # 设置用户密码
```

## 权限基础
```bash
chmod 755 filename    # rwxr-xr-x
chmod 644 filename    # rw-r--r--
chmod -R 755 dir/     # 递归设置
chown user:group file # 更改文件所有者
```

## 权限数字对照
- `r` = 4, `w` = 2, `x` = 1
- `755`：所有者rwx，组r-x，其他r-x
- `644`：所有者rw-，组r--，其他r--
- `600`：所有者rw-，组---，其他---

## sudo 配置
```bash
visudo    # 编辑sudoers文件
# 格式: username ALL=(ALL) NOPASSWD: /usr/bin/systemctl
```

## 常见权限问题

### Permission Denied 排查
1. 检查文件权限 `ls -la filename`
2. 检查目录权限（需要x权限才能进入目录）
3. 检查文件所有者 `ls -la filename`
4. 检查SELinux `ls -Z filename; getenforce`
5. 检查AppArmor `aa-status`

### 修复权限
```bash
# 修复web目录权限
chown -R www-data:www-data /var/www/html

# 修复SSH密钥权限（必须是600）
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub

# 修复sudoers权限
chmod 440 /etc/sudoers
```

## 特殊权限位
- **SUID**（s）：以文件所有者的权限执行（如 /usr/bin/passwd）
- **SGID**（s）：以目录所属组的权限创建文件
- **Sticky Bit**（t）：只有文件所有者可以删除自己的文件（如 /tmp）
```bash
chmod u+s file   # 设置SUID
chmod g+s dir    # 设置SGID
chmod +t dir     # 设置Sticky Bit
```
