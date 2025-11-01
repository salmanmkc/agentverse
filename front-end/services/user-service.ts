import { User } from "@/types/user"
import { mockUsers } from "@/lib/mock-data"

class UserService {
  private users: User[] = [...mockUsers]

  getUsers(): User[] {
    return this.users
  }

  getUserById(id: string): User | undefined {
    return this.users.find((u) => u.id === id)
  }

  getUsersByIds(ids: string[]): User[] {
    return this.users.filter((u) => ids.includes(u.id))
  }

  updateUser(id: string, updates: Partial<User>): void {
    const index = this.users.findIndex((u) => u.id === id)
    if (index !== -1) {
      this.users[index] = { ...this.users[index], ...updates }
    }
  }
}

export const userService = new UserService()
